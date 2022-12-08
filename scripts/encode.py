

def json_to_internal_format():
    # consumes AllPrintings.json, produces list of internally formated cards
    # drops those cards which are not suitable for the AI to train with
    pass  # TODO

def AI_to_internal_format():
    # consumes a single AI formatted string, produces a single internally formatted card
    pass  # TODO

def internal_format_to_human_readable(cards, out_path):
    # consumes a list of internally formatted cards, produces a yaml file
    pass  # TODO

def internal_format_to_AI_format():
    # consumes a single internal format, produces a single AI formatted string
    pass  # TODO

def limit_to_human_review_fields():
    # consumes a single internal format, returns internal format including only the fields fit for human review
    pass  # TODO

def validate():
    # consumes internal format, returns boolean
    # should return True for all canonical cards, but may be True or False for AI generated cards
    pass  # TODO

def error_correct_AI():
    # consumes AI format, returns AI format with error corrections applied
    # OR maybe consumes internal format, returns internal format with error corrections applied
    pass  # TODO

def unreversable_modification():
    # consumes a single internal format, produces a single internal format
    # makes changes which are not reversable by AI_to_internal_format
    # this fuinction will return the dataset which can be directly compared to the dual_processed format for validity
    #   such as standardizing order of keywords
    pass  # TODO

def encode_json_to_AI()
    # consumes AllPrintings.json
    # runs through encoding and decoding steps
    #   comapares encoded+decoded dataset to original dataset for end-to-end validity checking
    # produces several local data files for human comparison / debugging if validation fails
    # saves encoded data file to designated location

    cards_original = json_to_internal_format()
    validate()

    # save an unmodified dataset for human review
    internal_format_to_human_readable(cards_original, 'original_parsing.yaml')

    # TODO perform dataset modifications / standardizations which have no reverse


    # save the modified dataset for human review
    limited_cards = limit_to_human_review_fields(cards_original)
    internal_format_to_human_readable(limited_cards, 'original_limited.yaml')

    # transcribe to AI format, and save in designated location
    cards_AI = []
    for card in cards_original:
        cards_AI.append(internal_format_to_AI_format(card))
    f = open(out_path, 'w')  # TODO byte encoding to prevent unintended OS transcriptions?
    f.write('\n'.join(cards_AI))
    f.close()

    # decode AI format back to internal format for error checking
    cards_dual_processed = []  # TODO get a better name for this
    for card in cards_AI:
        cards_dual_processed.append(AI_to_internal_format(card))

    # save cards_dual_processed for human review
    internal_format_to_human_readable(cards_dual_processed, 'dual_processed.yaml')
    
