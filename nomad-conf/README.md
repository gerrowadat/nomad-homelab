# nomad-conf

In active hacking, do not use.


Usage outline: (mostly not implemented):

```
  - nomad-conf var [get|put|create|stat] # Basic variable manipulation

  - nomad-conf diff nomad/jobs/myjob:config /my/local/file

  - nomad-conf compare /my/local/file nomad/jobs/myjob:config # See which one is newer.


  - nomad-conf upload /my/local/file nomad/jobs/myjob:config
  - nomad-conf uploadall /my/local/files.d/*.cf nomad/jobs/myjob:config // concatenate into one file.
    --only-if-newer


  # long-running file or github integration
  - nomad-conf sync prometheus.yml nomad/jobs/prometheus:prometheus_yml
  - nomad-conf sync github.com/gerrowadat/homelab/monitoring/prometheus.yml nomad/jobs/prometheus:prometheus_yml
  # Also: Some means of doing a bunch of these, or a directory.
```

and so on.
