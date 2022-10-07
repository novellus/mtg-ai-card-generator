
# git-subtree management
* subtree list
	* [torch-rnn](https://github.com/jcjohnson/torch-rnn.git)
	    * &#x1F534; TODO modified with analogous changes from [billzorn's cousen-branch](https://github.com/billzorn/mtg-rnn)
	    * &#x1F534; TODO Sampling updated to specify specific substrings midsample (eg card names)
	    * &#x1F534; TODO  batching script branched, updated to take advantage of known information content. Both branches are used for different parts of the project. The new batcher is designed to consume data from [billzorn/mtgencode](https://github.com/billzorn/mtgencode) (mtg card text):
	        * batcher interprets the data as whole cards, and partitions cards between the splits instead of raw data chunks
	        * batch card order is randomized
	        * batcher randomizes the symbols in mana costs of cards, and the order of the fields in a card if the field's identity is specified by label rather than by order
	    * 
	* &#x1F534; TODO add more
* each subtree has a remote under the same name as the directory
* create remote: ```git remote add -f <dir> <url>```
* add subtree: ```git subtree add --prefix <dir> <remote> <branch> --squash```
* pull subtree: ```git fetch <remote> <branch>``` and then ```git subtree pull --prefix <dir> <remote> <branch> --squash```

