# Sphinx documentation

## install Sphinx
1. `pip install sphinx`
1. (option to use `sphinx_rtd_theme`) `pip install sphinx_rtd_theme`
   
## How to make docs directory and use sphinx
This section describes how we created the sphinx directory. You don't have to do it exactly like this, but it is for your reference.

1. make directory and start sphinx
```
$ pwd
/<working directory>/board-allocator
$ mkdir docs
$ sphinx-quickstart docs
... this is our settings ...
> Separate source and build directories (y/n) [n]: y[enter]
> Project name: board-allocator[enter]
> Author name(s): koheiito[enter]
> Project release []: 0.0.0[enter]
> Project language [en]:[enter]
..........................
```

2. change the configuration file<br>
Add the following code in the appropriate place
```
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon']
html_theme = 'sphinx_rtd_theme'
autoclass_content = 'both'
autodoc_default_options = {'private-members': True,
                           'show-inheritance': True}
```

3. change Makefile<br>
Add the following code in the appropriate place.
```
MODULEDIR     = ../

# files that do not need to be documented
EXCLUDEFILES  = ../cxtest.py ../mcc_test.py ../setup.py ../testcppmodule.py

# execute sphinx-apidoc
sphinx-apidoc:
	sphinx-apidoc -f -o $(SOURCEDIR) $(MODULEDIR) $(EXCLUDEFILES)
.PHONY: sphinx-apidoc

# build html
html: sphinx-apidoc
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
.PHONY: html
```

4. build html
```
$ pwd
/<working directory>/board-allocator
$ cd docs
$ make html
```