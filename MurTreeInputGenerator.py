import csv
import os
import logging

logger = logging.getLogger(__name__)

class MurTreeInputGenerator:
    def __init__(self, id_list):
        self.operator_id_list = id_list
        self.operator_dict = self.generate_dictionary(self.operator_id_list)
        self.operator_good_bad = self.generate_good_bad_operators(self.operator_id_list)

    def generate_good_bad_operators(self, id_list):
        good_bad_to_list = [tpl[1] for tpl in id_list]
        return good_bad_to_list

    def generate_dictionary(self, id_list):
        ids_to_list = [tpl[0] for tpl in id_list]
        id_dict = {key: [] for key in ids_to_list}
        return id_dict

    def update_dictionary_values(self, check_ids):
        to_list = [tpl[0] for tpl in check_ids]
        for key in self.operator_dict:
            self.operator_dict[key].append(1 if key in to_list else 0)

        return self.operator_dict

    def generate_murtree_input(self):
        result_lists = [list(values) for values in self.operator_dict.values()]
        result_tuple = (result_lists, self.operator_good_bad)
        # logger.info(result_tuple)
        return result_tuple
    
    def dump_to_file(self, path, action_name = "test"):
        names = ["rule", "rule1"]
        with open(os.path.join(path,f'tree_input_{action_name}.csv'), 'w') as csvfile:
            for key, item in self.operator_dict.items():
                s = ""
                for value in item:
                    s+= f"{value},"
                s = s.removesuffix(",")
                s +="\n"
                csvfile.write(s)
        csvfile.close()
