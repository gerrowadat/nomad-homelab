registry-mgr
============

This is a utility I use to make sure I have the right local images in my registry if I'm messing
about with versions of things. I try to use locally-fetched images where I can in case of an internet
outage, since a lot of the apps I run at home are only used at home. Often the only part that
needs outside internet access is the docker fetch if a job moves.

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


If I ever have to rebuild my registry from scratch, this can be used to 'pre-warm' the registry, I guess?

Also, see [//homelab/nomad/infra/docker-registry](https://github.com/gerrowadat/homelab/tree/main/nomad/infra/docker-registry) for hw I run 2 registries for mad reasons, and [where I configure the registry proxy on docker hosts](https://github.com/gerrowadat/homelab/blob/main/ansible/roles/docker/tasks/main.yml#L41)
