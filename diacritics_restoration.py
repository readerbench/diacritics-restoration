import pickle
from tabnanny import verbose

import numpy as np
import tensorflow as tf
from transformers import AutoTokenizer

import utils
from bert_cnn import weighted_categorical_crossentropy
from downloader import check_version, download_model
from lang import Lang


class DiacriticsRestoration(object):
    """
    Wrapper for Diacritics restoration
    """

    def __init__(self, verbose='silent'):

        self.bert_max_seq_len = 512
        self.max_windows = 280
        self.max_sentences = 10
        self.max_sentence_length = 256
        self.verbose = verbose # 0 -> 'silent', 1 -> 'auto'

        # load model
        if check_version(Lang.RO, ["models", "diacritice", "base"]):
            download_model(Lang.RO, ["models", "diacritice", "base"])

        self.model = tf.keras.models.load_model("resources/ro/models/diacritice/base", compile=False)
        self.tokenizer = AutoTokenizer.from_pretrained("readerbench/RoBERT-base")
        self.char_to_id_dict = pickle.load(open("resources/ro/models/diacritice/base/char_dict", "rb"))


    # replace_all: replaces all diacritics(if existing) with model predictions
    # replace_missing: replaces only characters that accept and don't have diacritics with model predictions; keeps existing diacritics
    def _process_string(self, string, mode="replace_all"):
        full_diacritics = set("aăâiîsștț")
        explicit_diacritics = set("ăâîșțĂÂÎȘȚ")
        if len(string) > self.max_sentence_length:
            result = ""
            for i in range(0, len(string), self.max_sentence_length):
                substring = string[i:min(len(string), i+self.max_sentence_length)]
                result += self._process_string(substring, mode)
            return result
        working_string = string.lower()
        clean_string = ""
        # remove everything not in char_to_id_dict
        for s in working_string:
            if s in self.char_to_id_dict.keys():
                clean_string += s

        working_string = clean_string
        working_string = ''.join([utils.get_char_basic(char) for char in working_string])

        diac_count = 0
        for s in working_string:
            if s in full_diacritics:
                diac_count += 1

        x_dataset = tf.data.Dataset.from_generator(lambda : utils.generator_bert_cnn_features_string(working_string, self.char_to_id_dict, 11, self.tokenizer, self.max_sentences, self.max_windows),
                        output_types=({'bert_input_ids': tf.int32, 'bert_segment_ids': tf.int32, 'token_ids': tf.int32, 'sent_ids': tf.int32,
                                        'mask': tf.float32, 'char_windows': tf.int32}, tf.float32),
                        output_shapes=({'bert_input_ids':[self.max_sentences, self.bert_max_seq_len], 'bert_segment_ids':[self.max_sentences, self.bert_max_seq_len], 'token_ids':[self.max_windows],
                                        'sent_ids': [self.max_windows], 'mask': [self.max_windows], 'char_windows': [self.max_windows, 11]}, [self.max_windows, 5]))
        x_dataset = x_dataset.batch(1)

        predictions = self.model.predict(x_dataset, steps=(diac_count//self.max_windows)+1, verbose=self.verbose)

        filtered_predictions = []
        for index in range(len(predictions[0])):
            if predictions[1][index] == 1:
                filtered_predictions.append(predictions[0][index])
        
        predictions = np.array(filtered_predictions)
        predicted_classes = list(map(lambda x: np.argmax(x), predictions))
        prediction_index = 0
        
        complete_string = ""
        for orig_char in string:

            lower_orig_char = orig_char.lower()

            if lower_orig_char in full_diacritics:
                if mode == "replace_all":
                    new_char = utils.get_char_from_label(utils.get_char_basic(lower_orig_char), predicted_classes[prediction_index])
                
                elif mode == "replace_missing":					
                    if lower_orig_char in explicit_diacritics:
                        new_char = lower_orig_char
                    else:
                        new_char = utils.get_char_from_label(utils.get_char_basic(lower_orig_char), predicted_classes[prediction_index])
                
                prediction_index += 1

                if orig_char.isupper():
                    new_char = new_char.upper()

            else:
                new_char = orig_char
            complete_string += new_char

        return complete_string

    # Eliminates problematic substrings from diacritics generation and calls _process_string for the rest
    def process_string(self, string, mode="replace_all"):
        
        substrings = string.split()
        problematic_indices = []
        start_index = 0
        
        for substring in substrings:
            start_index = string.find(substring, start_index)
            if len(substring) > 44: #Longest Romanian word is 44 letters long
                problematic_indices.append((start_index, start_index + len(substring)))
            start_index += len(substring)

        # Remove problematic substrings and process for diacritics
        new_string = string
        for start, end in reversed(problematic_indices):
            new_string = new_string[:start] + new_string[end:]

        result = self._process_string(new_string, mode)

        # Add problematic substring back into processed string
        for start, end in problematic_indices:
            result = result[:start] + string[start:end] + result[start:]

        return result