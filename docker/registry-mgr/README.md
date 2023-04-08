registry-mgr
============

TODO: Figure out how well a local registry with --registry-mirror deals with flakey interwebs.

This is a utility I use to make sure I have the right local images in my registry if I'm messing
about with versions of things. I try to use locally-fetched images where I can in case of an internet
outage, since a lot of the apps I run at home are only used at home. Often the only part that
needs outside internet access is the docker fetch of a job moves.

Get set up:

```
virtualenv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
python registry-manager.py --hcl_base=/root/of/my/hcl/files <verb> # You probably also want to set --local_docer_registry to your local registry's host:port
```

Current verbs are:

  - `list_images` - List all images mentioned in all files.
  - `check_local_registry` - Show the status of all mentioned images in the local registry:
    - *OK* - The version mentioned in the file is present.
    - *NO_VERSION* - the local registry has a different version of this image.
    - *MISSING* - The local registry has no version for this image.
  - `get_missing_versions` - Spit out shell commands to get missing versions.
  - `get_missing_images` - Spit out shell commands to get missing images.

my 2 use cases for this are:

  - If I'm upgrading a few apps, I'll edit my local .hcl files, then run `get_missing_versions`, mainly so I don't break the jobs and because I can never remember the docker commands.
  - If I ever have to rebuild my registry from scratch.
