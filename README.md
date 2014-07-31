#Stata Conference 2014

This repository contains or points to most of the code used in my presentation "Stata hybrids: updates and ideas". Instructions are given below for obtaining, configuring, and using this code.

##Obtaining these files

If you're a `git` user, you already know you can download this package with

    git clone https://github.com/jrfiedler/StataCon2014

If you're not a `git` user you can download a zip archive. If you're on the desktop version of the respository site,
there's a button for on the right for downloading the zip archive.

##Updates to Python projects

The GitHub repositories for last year's projects have been updated.

The code for embedding Python in Stata can be found [here](https://github.com/jrfiedler/python-in-stata).

The `stata_dta` module for working with .dta files in Python can be found [here](https://github.com/jrfiedler/stata-dta-in-python).

##New ideas

The code for the "new ideas" below are meant for demonstration purposes and might not always perform as desired. The code should work well enough to explore the ideas presented, and could be used as starting points for fully-developed tools, but they themselves are not yet fully-developed tools.

###New idea 1: Physical units in dta files

The code is [here](https://github.com/jrfiedler/StataCon2014/units_dta.py). This example requires Python 3, the `stata_dta` module from [here](https://github.com/jrfiedler/stata-dta-in-python) and the [Sympy module](http://docs.sympy.org/dev/install.html). 

This code assumes you will be opening a version 117 dta file (you might think of this as a "Stata 13" dta file), but it should also work with versions 115 and 114 ("Stata 11 and 12" dta files).


###New idea 2: Multimedia data viewer

####Requirements:

1. [SlickGrid](https://github.com/mleibman/SlickGrid) (which supplies most of the functionality)
2. [StataDta.js](https://github.com/jrfiedler/StataDtaJS) for reading the .dta file into JavaScript
3. [`read_dta.html`](https://github.com/jrfiedler/StataCon2014/read_dta.html) (from this repository)
4. A modern web browser that supports the `DataView` interface. In particular I recommend using a recent version of Firefox or Google Chrome.
5. (Optional) The example data set with binary data, `birds.dta`, and the 'formatted' version of the same data set, `birds_formatted.dta`, included in this repository.


The html file assumes that `StataDta.js` is in the same directory and that SlickGrid has been cloned into the parent directory of the html file. Of course, you could specify a different arrangement by making the necessary changes to the html file.

Once you have the files and directories arranged, simply open the html file in your browser (again, I recommend Firefox or Chrome), and click on "Choose File" to open a .dta file.


###New idea 3: Notebook interface


####Requirements:

1. Windows OS (required for the interaction between Python and Stata)
2. Python
3. The `win32com` module (many Python distributions for Windows will include this)
4. IPython and the IPython Notebook
5. The `ipython_notebook_config.py` and `stata_interface.py` files included in this repository.
6. (Optional) If you want help files to show up inline, you will need a modified version of the user-written Stata command `log2html`. See instructions in "Modifying `log2html`" below.


####Installation:

1. If you've never used Stata automation on Windows, you will probably need to register Stata. See [here]() for instructions.

2. Create a new IPython 'profile' with

        ipython profile create profile_name

    replacing `profile_name` with the desired name, possibly `stata`. 

3. Find the directory for the new profile. For example, mine is found at
 
        C:\Users\user_name\.ipython\profile_name

4. Replace the `ipython_notebook_config.py` in that directory with the one from this repository, and put the `stata_interface.py` file in the `startup` sub-directory.

5. In `stata_interface.py` change the directories to where you would like notebook files to be saved.

6. In `stata_interface.py`, near the top, there is a section called "customization". Make any necessary changes to the values in that section.

7. Start the IPython notebook interface with the new profile:

        ipython ntoebook --profile profile_name
 
    Then create a new notebook. An instance of Stata should be created automatically (give it a few seconds to open). Commands entered in the notebook should be sent to Stata, and you should see the Stata results appear in the notebook.

8. If you need instructions for how to use the notebook, or how to create a new notebook (as in the last step), start [here](http://ipython.org/notebook.html). At the time of this writing that page links to resources for learning about the IPython Notebook and has an embedded video demonstrating usage.


####(Optional) modifying `log2html`

First, you will have to obtain a copy of `log2html`, probably by doing

    ssc install log2html

inside of Stata. Find the `log2html.ado` file and save a copy of it as `sthlp2html.ado` somewhere where Stata can find it (for example, in your `personal` directory, or in your `plus` directory in a sub-directory called `s`).

In the new `sthlp2html.ado` file, make the following changes:

1. On line 8, change `program log2html` to `program sthlp2html`.

2. In line 10, 11, or 12 (or thereabouts), add the option `saveas(str asis)`.

3. Replace lines 74-83:

        local origfile `smclfile'
        if (!index(lower("`origfile'"),".smcl")) {
		    local origfile  "`origfile'.smcl"
        }
        local smclfile : subinstr local smclfile ".smcl" "" 
        local smclfile : subinstr local smclfile ".SMCL" ""
        local smclfile : subinstr local smclfile `"""' "", all /* '"' (for fooling emacs) */
        local smclfile : subinstr local smclfile "`" "", all 
        local smclfile : subinstr local smclfile "'" "", all 
        local outfile `"`smclfile'.html"'

    with

        local origfile `smclfile'
        if (!index(lower("`origfile'"),".sthlp") & !index(lower("`origfile'"),".hlp")) {
            local origfile  "`origfile'.sthlp"
        }
	
        local pos = max(strpos(`"`sthlpfile'"', "/"), strpos(`"`sthlpfile'"', "\"))
        while (`pos' != 0) {
            local sthlpfile = substr(`"`sthlpfile'"', `pos' + 1, .)
            local pos = max(strpos(`"`sthlpfile'"', "/"), strpos(`"`sthlpfile'"', "\"))
        }
		
        if ("`saveas'" == "") {
            local smclfile : subinstr local sthlpfile ".sthlp" "" 
            local smclfile : subinstr local sthlpfile ".STHLP" ""
            local smclfile : subinstr local sthlpfile ".hlp" "" 
            local smclfile : subinstr local sthlpfile ".HLP" ""
            local smclfile : subinstr local sthlpfile `"""' "", all /* '"' (for fooling emacs) */
            local smclfile : subinstr local sthlpfile "`" "", all 
            local smclfile : subinstr local sthlpfile "'" "", all 
            mata: st_local("outfile", pathjoin(st_local("saveas"), "`smclfile'.html"))
            local outfile `"`smclfile'.html"'
        }
        else {
            local outfile `"`saveas'"'
        }
