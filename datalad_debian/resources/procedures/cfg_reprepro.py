import sys
import datalad.api as dl

ds = dl.Dataset(sys.argv[1])
repo = ds.repo

# the actual repository should be separately accessible
# (via webserver) and is therefore placed into a dedicated
# subdataset, which we can publish individually. we can also
# further subdivide it for large repos
# do not register immediate in the superdataset, but consolidate
# in a single commit at the end
dl.create(ds.pathobj / 'repo')

# destination for the reprepro config
(ds.pathobj / 'conf').mkdir()
# we want the config to be in git
repo.call_annex(['config', '--set', 'annex.largefiles', 'exclude=conf/*'])
# establish basic config for repository and reprepro behavior
(ds.pathobj / 'conf' / 'options').write_text("""\
# we want repropro to ask for a key passphrase and not just die
ask-passphrase
# tell reprepro where the repository root is (root of the subdataset)
outdir +b/repo
""")
# the DB files written and read by reprepro need special handling
# we need to keep them unlocked (for reprepro to function normally
# without datalad), but we also do not want them in git, and we also
# cannot fully ignore them: make sure the anything in db/ is tracked
# but always unlocked
repo.call_annex(['config', '--set', 'annex.addunlocked', 'include=db/*'])

# place some default repo config to make obvious what needs to go
# where
(ds.pathobj / 'conf' / 'distributions').write_text("""\
Codename: buster
Components: main
Architectures: i386 amd64
SignWith: 7FFB9E9B
""")

ds.save(
    path=['conf', 'repo'],
    message='Basic reprepro setup',
)
