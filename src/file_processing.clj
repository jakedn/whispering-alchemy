(ns file-processing
  (:require [babashka.process :as p]
            [babashka.fs :as fs]
            [clojure.string :as str]
            [babashka.pods :as pods]
            [run-podman :as rp]))

(def ^:dynamic *verbose* false)
(def sony-format {:pattern #"(\d{2})(\d{2})(\d{2})_(\d{4})(_\d{2})?\.(wav|mp3)"
                  :func (fn [[_ yy mm dd tttt num]]
                          (str "20" yy "-" mm "-" dd "_" tttt num "_"))})

(defn formats-vec [] [sony-format])

(defn verbose-print
  "Prints a message if *verbose* is true."
  [& args]
  (when *verbose*
    (apply println args)))

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
          (verbose-print "Moved " file-name " -> " new-name)))))

(defn process-intake [intake-dir rename-dir]
  (doseq [file (fs/list-dir intake-dir)]
    (rename-file file rename-dir)))

(defn transcribe-file
  "Transcribe a given file with the given model using whisper AI."
  ([file] (transcribe-file file "base"))
  ([file model]
   (let [file-name (fs/file-name file)
         file-dir (fs/parent file)
         [base-name ext] (fs/split-ext file-name)
         out-file (str base-name "." model ".txt")
         out-file-path (fs/file file-dir out-file)
         audio? (some #(= % ext) ["mp3" "wav"])
         trans-exists? (fs/exists? out-file-path)
         good-size? (and (> (fs/size file) 100)
                         (< fs/size file 20000000))
         do-trans? (and audio? (not trans-exists?) (not good-size?))
         opts (cond-> ["--model" model]
                *verbose* (conj "-v"))]
     (when audio?
       (verbose-print "Transcribing file: " file-name)
       (when trans-exists?
         (verbose-print "Transcription exists ... skipping"))
       (when (not good-size?)
         (verbose-print "File is to small or to big ... skipping")))
     (when do-trans?
       (spit out-file-path (apply rp/transcribe-audio file opts))
       (verbose-print "Transcribed file: " file-name " to " out-file)))))

(defn transcribe-all
  "Runs transcribe file on all file in a specific directory with a given model."
  ([dir] (transcribe-all dir "base" 100))
  ([dir model] (transcribe-all dir model 100))
  ([dir model max]
   ;TODO add maximum transcribtion amount
   (doseq [file (fs/list-dir dir)]
    (transcribe-file file model))))

(defn -main []
  ;rename files
  ;sort files
  ;transcribe files in trans dir
  )