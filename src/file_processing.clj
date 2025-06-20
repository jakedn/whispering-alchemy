(ns file-processing
  (:require [babashka.process :as p]
            [babashka.fs :as fs]
            [clojure.string :as str]
            [babashka.pods :as pods]
            [run-podman :as rp]))

(def SUCCESS 0)
(def ^:dynamic *verbose* false)
(def ^:dynamic *min-file-size* 100)
(def ^:dynamic *max-file-size* 15000000)

(def sony-format {:pattern #"(\d{2})(\d{2})(\d{2})_(\d{4})(_\d{2})?\.(wav|mp3|m4a|aac|flac)"
                  :func (fn [[_ yy mm dd tttt num]]
                          (str "20" yy "-" mm "-" dd "_" tttt num "_"))})

(defn formats-vec [] [sony-format])

(defn verbose-print
  "Prints a message if *verbose* is true."
  [& args]
  (when *verbose*
    (apply println args)))

(defn run-x-times
  "Takes in a function and sequence of inputes for that function.
   It runs the function on each element of the sequence or until it reaches max successes"
  [func input-seq success-code max & args]
  (reduce (fn [acc elem]
            (if (< acc max)
              (if (= success-code
                     (apply func elem args))
                (+ acc 1) acc)
              acc))
          0 input-seq))

(defn rename-file
  ""
  [file rename-dir]
  (verbose-print "Renaming file: " file)
  (let [file-name (fs/file-name file)
        file-ext (second (fs/split-ext file-name))
        convert (fn [{:keys [pattern func]} string]
                  (let [match (re-matches pattern string)
                        new-str (if match (func match) nil)]
                    new-str))
        new-name-prefix (some identity (map convert (formats-vec) (repeat file-name)))
        bad-format? (nil? new-name-prefix)
        opts (if *verbose* ["-v"] [])
        words (if bad-format? nil (apply rp/get-words file opts))
        new-name (str new-name-prefix (str/join "-" words) "." file-ext)]
    (if bad-format?
      (do (verbose-print "File: " file-name " doesn't have supported format.\n")
          1)
      (do (fs/move file (fs/path rename-dir new-name))
          (verbose-print "Moved " file-name " -> " new-name)
          SUCCESS))))

(defn process-intake
  "Runs rename-file on all files in a specific directory. Moves them to the rename-dir specified.
   When max is specified, only 'max' transcriptions will occur otherwise max is 100."
  ([intake-dir] (process-intake intake-dir intake-dir))
  ([intake-dir rename-dir] (process-intake intake-dir rename-dir 100))
  ([intake-dir rename-dir max]
   (run-x-times rename-file (fs/list-dir intake-dir) SUCCESS max rename-dir)))

(defn transcribe-file
  "Transcribe a given file with the given model using whisper AI."
  ([file] (transcribe-file file "base"))
  ([file model]
   (let [file-name (fs/file-name file)
         file-dir (fs/parent file)
         [base-name ext] (fs/split-ext file-name)
         out-file (str base-name "." model ".txt")
         out-file-path (fs/file file-dir out-file)
         audio? (some #(= % ext) ["mp3" "wav" "m4a" "aac" "flac"])
         trans-exists? (fs/exists? out-file-path)
         ;; todo get rid of magic numbers
         file-size (fs/size file)
         good-size? (and (> file-size *min-file-size*) 
                         (< file-size *max-file-size*))
         do-trans? (and audio? (not trans-exists?) good-size?)
         opts (cond-> ["--model" model]
                *verbose* (conj "-v"))]
     (when audio?
       (verbose-print "Transcribing file: " file-name)
       (cond
         trans-exists?    (verbose-print "Transcription exists ... skipping")
         (not good-size?) (verbose-print "File is to small or to big ... skipping")))
     (when do-trans?
       (spit out-file-path (apply rp/transcribe-audio file opts))
       (verbose-print "Transcribed file: " file-name " to " out-file)
       SUCCESS))))

(defn transcribe-all
  "Runs transcribe file on all file in a specific directory with a given model.
   When max is specified, only 'max' transcriptions will occur."
  ;; todo get reid of magic numbers
  ([dir] (transcribe-all dir "base"))
  ([dir model] (transcribe-all dir model 100))
  ([dir model max]
   (run-x-times transcribe-file (fs/list-dir dir) SUCCESS max model)))

(defn -main []
  ;rename files
  ;sort files
  ;transcribe files in trans dir
  )