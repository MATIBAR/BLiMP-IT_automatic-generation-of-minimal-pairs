import pandas as pd
import random
import logging
import re

# Set up logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Add a global dictionary to track used words per tag
global_used_words_by_tag = {}

def load_tag_sequences(file_path):
    """
    Load tag sequences from a CSV file containing good and bad sequence pairs.
    Expected CSV format: two columns named 'Good_Sequence' and 'Bad_Sequence'
    """
    try:
        df = pd.read_csv(file_path)
        if 'Good_Sequence' not in df.columns or 'Bad_Sequence' not in df.columns:
            raise ValueError("CSV file must contain 'Good_Sequence' and 'Bad_Sequence' columns")

        sequences = []
        for _, row in df.iterrows():
            good_seq = str(row['Good_Sequence']).strip()
            bad_seq = str(row['Bad_Sequence']).strip()
            if good_seq and bad_seq:  # Only add non-empty sequences
                sequences.append((good_seq, bad_seq))

        if not sequences:
            raise ValueError("No valid sequences found in the file")

        return sequences

    except Exception as e:
        logging.error(f"Error loading tag sequences: {str(e)}")
        raise

def load_lexicon(file_path):
    df = pd.read_csv(file_path)
    lexicon = {}
    for _, row in df.iterrows():
        word = str(row['Word']).strip()
        tag = str(row['Tag']).strip()
        if tag not in lexicon:
            lexicon[tag] = []
        lexicon[tag].append(word)
    return lexicon

def get_base_tag(tag):
    return re.sub(r'[₁₂₃₄₅₆₇₈₉]', '', tag.upper())

def get_tag_number(tag):
    match = re.search(r'[₁₂₃₄₅₆₇₈₉]', tag)
    return match.group(0) if match else None

def get_verb_root(verb):
    """Get the root of an Italian verb."""
    if verb.endswith('ano'):
        return verb[:-3]
    elif verb.endswith('ono'):
        return verb[:-3]
    elif verb.endswith('a'):
        return verb[:-1]
    elif verb.endswith('e'):
        return verb[:-1]
    return verb

def get_word_for_tag(tag, lexicon, used_words):
    """Get a word for a given tag from the lexicon with improved variety."""
    base_tag = re.sub(r'[₁₂₃₄₅₆₇₈₉]$', '', tag)

    if base_tag not in lexicon:
        logging.warning(f"Tag not found in lexicon: '{base_tag}' (original tag: '{tag}')")
        return f"[Unknown tag: '{tag}']"

    # Initialize global tracking for this tag if not already done
    if base_tag not in global_used_words_by_tag:
        global_used_words_by_tag[base_tag] = set()

    # First try: Get words not used globally for this tag
    available_words = [w for w in lexicon[base_tag]
                      if w not in used_words and
                      w not in global_used_words_by_tag[base_tag]]

    # Second try: If all words have been used globally, reset the global tracking for this tag
    if not available_words:
        global_used_words_by_tag[base_tag].clear()
        available_words = [w for w in lexicon[base_tag] if w not in used_words]

    # Final try: If still no words available, use any word for the tag
    if not available_words:
        available_words = lexicon[base_tag]

    word = random.choice(available_words)
    used_words.add(word)
    global_used_words_by_tag[base_tag].add(word)
    return word

def find_matching_verb_pair(lexicon, singular_tag, plural_tag):
    """Find a matching singular-plural verb pair in the lexicon based on verb roots."""
    singular_base_tag = re.sub(r'[₁₂₃₄₅₆₇₈₉]$', '', singular_tag)
    plural_base_tag = re.sub(r'[₁₂₃₄₅₆₇₈₉]$', '', plural_tag)

    singular_verbs = lexicon.get(singular_base_tag, [])
    plural_verbs = lexicon.get(plural_base_tag, [])

    if not singular_verbs or not plural_verbs:
        return None, None

    random.shuffle(singular_verbs)
    for singular_verb in singular_verbs:
        root = get_verb_root(singular_verb)
        matching_plurals = [v for v in plural_verbs if get_verb_root(v) == root]

        if matching_plurals:
            plural_verb = random.choice(matching_plurals)
            return singular_verb, plural_verb

    return None, None

def generate_sentence_pair(good_sequence, bad_sequence, lexicon):
    words = {}
    used_words = set()
    good_sentence = []
    bad_sentence = []

    good_tags = good_sequence.split()
    bad_tags = bad_sequence.split()

    verb_positions = []
    verb_subscripts = {}

    for i, (good_tag, bad_tag) in enumerate(zip(good_tags, bad_tags)):
        if 'VERB' in good_tag and 'VERB' in bad_tag:
            good_subscript = get_tag_number(good_tag)
            bad_subscript = get_tag_number(bad_tag)

            if good_subscript and good_subscript == bad_subscript:
                if good_subscript not in verb_subscripts:
                    verb_subscripts[good_subscript] = []
                verb_subscripts[good_subscript].append(i)
                verb_positions.append(i)

    for i, tag in enumerate(good_tags):
        if i not in verb_positions:
            word = get_word_for_tag(tag, lexicon, used_words)
            good_sentence.append(word)
        else:
            good_sentence.append(None)

    for i, tag in enumerate(bad_tags):
        if i not in verb_positions:
            if good_tags[i] == bad_tags[i]:
                bad_sentence.append(good_sentence[i])
            else:
                word = get_word_for_tag(tag, lexicon, used_words)
                bad_sentence.append(word)
        else:
            bad_sentence.append(None)

    for subscript, positions in verb_subscripts.items():
        pos = positions[0]
        good_tag = good_tags[pos]
        bad_tag = bad_tags[pos]

        max_attempts = 50
        for attempt in range(max_attempts):
            singular_verb, plural_verb = find_matching_verb_pair(lexicon, good_tag, bad_tag)
            if singular_verb is not None:
                for p in positions:
                    good_sentence[p] = singular_verb
                    bad_sentence[p] = plural_verb
                break
        else:
            raise ValueError(f"Could not find matching verb pair after {max_attempts} attempts")

    good_sentence = [word if word is not None else "[MISSING]" for word in good_sentence]
    bad_sentence = [word if word is not None else "[MISSING]" for word in bad_sentence]

    return ' '.join(good_sentence), ' '.join(bad_sentence)

def main():
    lexicon_file = '/content/NUOVO_LESSICO_AGGIORNATO.csv'
    tag_sequences_file = '/content/tags_sequences_LEXICON_17.csv'
    total_pairs_to_generate = 120

    try:
        lexicon = load_lexicon(lexicon_file)
        sequences = load_tag_sequences(tag_sequences_file)

        print("\nGenerated Sentence Pairs:")
        used_combinations = set()
        pairs_generated = 0
        attempts = 0
        max_attempts = total_pairs_to_generate * 10

        while pairs_generated < total_pairs_to_generate and attempts < max_attempts:
            try:
                good_seq, bad_seq = random.choice(sequences)
                good_sentence, bad_sentence = generate_sentence_pair(good_seq, bad_seq, lexicon)

                key = (good_sentence, bad_sentence)
                if key not in used_combinations:
                    pairs_generated += 1
                    used_combinations.add(key)
                    print(f"\nPair {pairs_generated}:")
                    print(f"Good: {good_sentence}")
                    print(f"Bad:  {bad_sentence}")
                    print(f"Good Sequence: {good_seq}")
                    print(f"Bad Sequence:  {bad_seq}")

            except ValueError as e:
                logging.debug(f"Retrying due to: {str(e)}")

            attempts += 1

        if pairs_generated < total_pairs_to_generate:
            logging.warning(f"Could only generate {pairs_generated} unique pairs out of {total_pairs_to_generate} requested")

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
