import sys
import datalad.api as dl

ds = dl.Dataset(sys.argv[1])
repo = ds.repo

to_save = []

for f, c in (
        (ds.pathobj / 'recipes' / 'README.md',
         "This directory contains the recipes for all build pipeline images."),
        (ds.pathobj / 'envs' / 'README.md',
         "This directory contains build pipeline images."),
):
    if not f.exists():
        f.parent.mkdir(exist_ok=True)
        f.write_text(c)
        to_save.append(f)

for f, a in (
        # all recipes go into Git
        (repo.pathobj / 'recipes' / '.gitattributes',
         [('*', {'annex.largefiles': 'nothing'})]),
        (repo.pathobj / 'envs' / '.gitattributes',
         [('*.md', {'annex.largefiles': 'nothing'})]),
):
    if not f.exists():
        repo.set_gitattributes(a, f)
        to_save.append(f)

# ignore a cache/ dir, may not be used by all setups,
# but adds a little convenience for those who do
gitignore = repo.pathobj / '.gitignore'
if not gitignore.exists():
    gitignore.write_text("cache\n")
    to_save.append(gitignore)

ds.save(
    path=to_save,
    message='Debian builder dataset setup',
)
