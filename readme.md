
# git-subtree management
* each subtree has a remote under the same name as the directory
	* [torch-rnn](https://github.com/jcjohnson/torch-rnn.git)
	* TODO
* create remote: ```git remote add -f <dir> <url>```
* add subtree: ```git subtree add --prefix <dir> <remote> <branch> --squash```
* pull subtree: ```git fetch <remote> <branch>``` and then ```git subtree pull --prefix <dir> <remote> <branch> --squash```

