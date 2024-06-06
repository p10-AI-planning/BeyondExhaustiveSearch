import logging.config
import pickle
import time
import shutil
import os
import logging
from DataObjects.DecisionTree import RuleDecisionTree
from DataObjects.Problem import Problem
from DataObjects.ConfusionMatrix import ConfusionMatrix
from DomainParser import PDDLDomain
from DataHandler.DatabaseHandlerV2 import DatabaseHandlerV2
from ExampleGenerator import ExampleGenerator
from DataObjects.DecisionTree.RuleDecisionTree import RuleDecisionTree

logger = logging.getLogger(__name__)
path = os.path.dirname(__file__)

class Evaluator:

    @staticmethod
    def evaluator(dominsToEval: list[str], testing_set):
        models_path = os.path.join(path, "TrainedModels")
        models = os.listdir(models_path)
        
        result_path = os.path.join(path, "evaluations")
        if os.path.exists(result_path):
            shutil.rmtree(result_path)    
        os.mkdir(result_path)

        logger.info(f"Running evaluator for {len(models)} models")
        model_dict = {"": RuleDecisionTree}
        confusion_matrix_dict = {"": ConfusionMatrix}
        total_operators_negative = {"": 0}
        total_operators_positive = {"": 0}

        for model in models:
            if model.endswith(".rar"):
                continue
            confusion_matrix_dict.clear()
            total_operators_negative.clear()
            total_operators_positive.clear()
            model_dict.clear()

            info = model.split("_")
            domain_name = info[1]
            if len(dominsToEval) > 0 and domain_name not in dominsToEval:
                continue
            if len(info) == 4:
                training_set = info[2]
                time_setting = info[3]
            else:
                training_set = f"{info[2]}_{info[3]}"
                time_setting = info[4]
            logger.info(f"Runing for model: {model}]")
            test_data_path = os.path.join(path, "TestingData", testing_set, domain_name)
            #test_data_path = os.path.join(path, "Data", "autoscale-learning", domain_name, "training_100_0.7")
            domain = PDDLDomain.from_pddl_file(os.path.join(test_data_path, "domain.pddl"))
            
            domain_output_folder = os.path.join(result_path, domain.name)
            model_path = os.path.join(models_path, model)
            if not os.path.exists(domain_output_folder):
                os.mkdir(domain_output_folder)
            if os.path.isfile(os.path.join(model_path, "model_run_info.csv")):
                shutil.copy(os.path.join(model_path, "model_run_info.csv"),os.path.join(domain_output_folder,f"{model}_run_info.csv"))


            data_handler = DatabaseHandlerV2(domain, False, False)
            example_generator = ExampleGenerator()
            examples :list[Problem] = example_generator.generat_problem_examples(test_data_path, domain)
            for key, action in domain.actions.items():
                file_name = f"model_{domain.name}_{action.name}.rulemodel"
                confusion_matrix_dict[action.name] = ConfusionMatrix()
                if os.path.isfile(os.path.join(models_path, model, file_name)):
                    with open(os.path.join(models_path, model, file_name),'rb') as model_file:
                        model_dict[action.name] = pickle.load(model_file)
                        model_dict[action.name].add_data_handler(data_handler)
            
            if len(model_dict) == 0:
                logger.info(f"Model {model} contains no actions skipping")
                continue

            for problem in examples:
                data_handler.clear_all_tables()
                data_handler.insert_problem(problem)
                for action, example in problem.problemExamples.items():
                    if action not in total_operators_negative.keys():
                            total_operators_negative[action] = 0
                    if action not in total_operators_positive.keys():
                            total_operators_positive[action] = 0

                    if action in model_dict.keys():
                        model_dict[action].clear_cache()
                        for operator in example.negatives:#bad operators
                            if model_dict[action].evaluate(tuple(operator)): #Model says good, actual bad = FP
                                confusion_matrix_dict[action].FP += 1
                            else: #Model says bad, actual bad = TN
                                confusion_matrix_dict[action].TN += 1
                            total_operators_negative[action] += 1

                        for operator in example.positives:#good operators
                            if tuple(operator) == (18,2,16,5,1) or tuple(operator) == (18,2,11,5,1):  
                                print("hej")
                            if model_dict[action].evaluate(tuple(operator)): #Model says good, actual good = TP
                                confusion_matrix_dict[action].TP += 1
                            else: #Model says bad, actual good = FN
                                confusion_matrix_dict[action].FN += 1
                            total_operators_positive[action] += 1

            logger.info(f"Evaltion of {model} completed")
            data_handler.db_connection.close()

            logger.info(f"Creating output: {file_name}")
            file_name = f"{model}_evaluation.csv"
            full_file_path = os.path.join(domain_output_folder, file_name)
            if os.path.exists(full_file_path):
                os.remove(full_file_path)

            csv_file = open(full_file_path,"w")
            csv_file.write("action,positives,negatives,TP,FN,FP,TN,precision,accuracy,recall,F1\n")
            
            for key, cm in confusion_matrix_dict.items():
                log_str = f"{key}, positives: {total_operators_positive[key]}, negatives: {total_operators_negative[key]}, TP: {cm.TP}, FN: {cm.FN}, FP: {cm.FP}, TN: {cm.TN}," 
                log_str += f"precision:{round(cm.precision(),3)}, accuracy: {round(cm.accuracy(),3)}, recall: {round(cm.recall(),3)}, f1: {round(cm.f1(),3)}"
                logger.info(log_str)
                out_str = f"{key},{total_operators_positive[key]},{total_operators_negative[key]},{cm.TP},{cm.FN},{cm.FP},{cm.TN},"
                out_str += f"{round(cm.precision(),3)},{round(cm.accuracy(),3)},{round(cm.recall(),3)},{round(cm.f1(),3)}\n"
                csv_file.write(out_str)
            csv_file.close()
            logger.info(f"Evaluation result written to: {file_name}")