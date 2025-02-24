(ns run-podman
  (:require [babashka.process :as p]
            [babashka.fs :as fs]))
                     

;; this part was from a time where file would be copied to a tmp dir
;; asses removing in later release
;; move this comment to issue on github
(defn random-tmp-dir [name]
  (let [alphabet "abcdef0123456789"]
    (apply str (concat [name "-"] (repeatedly 8 #(rand-nth alphabet))))))

(def tmp-dir (random-tmp-dir "/tmp/cvol"))

(defn- command
  "build the podman command to be used with process/shell"
  [model-dir & opts]
  (apply concat ["podman" "run" "--rm" "-i"
                 "--name=whisper-app"
                 "--network" "none"
                 "-v" (str model-dir ":/model-dir:z")
                 ;"-v" (str tmp-dir ":/app:z")
                 "--tmpfs" "/app/tmp:size=1G"
                 "whisper-cpu"]
         opts))

(defn transcribe-audio 
  "takes in a file path of an audio file and runs it through whispering alchemy container
   This function will return the stdout of the container and print the stderr to console
   Take note of the options from whispering alchemy."
  ;known issue when audio-file-ext is given, its appended twice
  [file-path model-dir & opts]
  (let [file-ext (fs/extension file-path)
        new-opts (concat opts ["--audio-file-ext" file-ext])
        process-opts {:in (fs/file file-path) :out :string :err :string}
        command-vec (command model-dir new-opts)
        process (apply p/shell process-opts command-vec)]
    (println (:err process))
    (:out process)))