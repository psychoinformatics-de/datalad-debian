# Debian+DataLad setup
# goals:
# - flexible publication
# - ability to expose multiple version of a repository (cheaply)
# - all sensitive data (keys, config) remains local
set -e -u -x

workdir=$(pwd)

# the demo has a few pieces
# the local clone of the dataset that hold all the info
datalad -c "datalad.locations.extra-procedures=$(pwd)" \
    create -c reprepro reprepro_setup

# a datalad store to hold all the annex'ed Debian repository content
# (on a remote server)
mkdir datastore
# the public-facing repository (on the same remote server)
mkdir www
# some pieces just for this tmp
mkdir tmp

# get a demo deb package
wget -O tmp/hello_2.10-2_amd64.deb http://deb.debian.org/debian/pool/main/h/hello/hello_2.10-2_amd64.deb

# we publish the public facing data to a dataset store
# we (could) do recursive to cover any number of subdatasets
# we could publish to ria+ssh and not just local
cd reprepro_setup/repo
datalad create-sibling-ria -r -s debianstore "ria+file://${workdir}/datastore"
datalad push -r --to debianstore

cd "$workdir"

# at this point we can run reprepro wrapped into datalad-run
# always run in the root of the reprepro_setup
datalad -C reprepro_setup run reprepro includedeb buster "${workdir}/tmp/hello_2.10-2_amd64.deb"

# now we can publish this update (just the public side) to the dataset store
datalad -C reprepro_setup/repo push --to debianstore

# and we can set up any number of exposed repository states
datalad clone \
  --reckless ephemeral \
  "ria+file://${workdir}/datastore#$(datalad -f '{infos[dataset][id]}' -C reprepro_setup/repo wtf -S dataset)" \
  www/debian

# given proper permissions, exposing www/debian via a webserver should yield a functional repository


# === update cycle ====
# produce package
wget -O tmp/hello-traditional_2.10-5_amd64.deb http://deb.debian.org/debian/pool/main/h/hello-traditional/hello-traditional_2.10-5_amd64.deb
# ingest
# note
datalad -C reprepro_setup run -o db/ reprepro includedeb buster "${workdir}/tmp/hello-traditional_2.10-5_amd64.deb"
# push all changes since the last push to (remote) server
datalad -C reprepro_setup/repo push -r --to debianstore --since ^
# on the remote server, sync the public-facing repository
# because we are using an ephemeral clone with a symlink'ed annex, we do not need to actually `get` any files
datalad -C www/debian update --merge -s origin
# === end update cycle ====
