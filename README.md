[![Build Status](https://travis-ci.com/xyla-io/raspador.svg?token=TOKEN&branch=master)](https://travis-ci.com/xyla-io/raspador)

# raspador

A Xyla scraper.

## Install

### Install Visual Studio Code

Download and install Microsoft Visual Studio Code from https://code.visualstudio.com/download

Open the app and select the terminal tab in the bottom pane to run terminal commands for the remaining installation steps.

### Install git

Git is a version control system used to manage development of the Raspador codebase.

#### OS X

Install Xcode using the App Store app, and open the Xcode app to install the command line tools.

To check that Git is installed, run this terminal command

```bash
which git
# the path to the git executable should be printed
# if nothing is printed, git is not installed

# if git is installed clone the Raspador repo
git clone https://github.com/xyla-io/raspador.git
```

#### Windows

Download the Git for Windows Setup from https://git-scm.com/download/win and install git.

```bash
git clone https://github.com/xyla-io/raspador.git
```

### Install Python

Raspador is written in Python and requires Python 3 to be installed.

#### OS X

##### Install homebrew

Homebrew is a package manager for OS X, similar to a free, command-line app store (See https://brew.sh/).

```bash
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
```

With homebrew, install Python 3.6.1

```bash
brew install python3
brew switch python3 3.6.1
```

#### Windows

Download and install Python 3.6.1 from https://www.python.org/downloads/windows/

### Install geckdriver

`geckodriver` allows the selenium python package to drive Firefox.

- https://github.com/mozilla/geckodriver/releases

### Install Python virtual environment

Create a virtual Python environment for running Raspador.

```bash
# in the raspador root directory
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd development_packages/data_layer/packages/mysql-connector-python-2.1.7
python setup.py install
cd ../..
python setup.py develop
cd ..
deactivate
```

### Create a Firefox profile

Create a user profile in Firefox for the scraper to use.

- https://support.mozilla.org/en-US/kb/profile-manager-create-and-remove-firefox-profiles

## Run

Open the raspador root directory in Visual Studio Code and Run Raspador from the terminal.

```bash
source .venv/bin/activate
python main.py <CONFIGURATION> <STARTDATE> <ENDDATE>
```

### Docker

#### Install docker

```bash
apt-get update
apt-get install docker.io
# add permissions for the user who will run docker images
usermod -a -G docker <USER>
```

#### Build docker image

```bash
# in the project root
docker build -t raspador .
```

#### Run with docker

```bash
docker run --rm --privileged -p 4000:4000 -it raspador bash /usr/src/app/run.sh --help
```
