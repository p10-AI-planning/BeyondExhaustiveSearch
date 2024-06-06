import logging.config
import pickle
import time
import os
import sys
import shutil
import tarfile
import numpy
import pddl
import logging
import random
from datetime import datetime
from pddl import parse_problem
from pddl import parse_domain
from GOFAI import plan
from DataObjects.DecisionTree import RuleDecisionTree
from DataObjects.DecisionTree.Model import Model
from DataObjects.DecisionTree.MurTreeGenerator import MurTreeGenerator
from DataObjects.Problem import Problem
from DataObjects.ConfusionMatrix import ConfusionMatrix
from DomainParser import PDDLDomain
from DataHandler.DatabaseHandlerV2 import DatabaseHandlerV2
from ExampleGenerator import ExampleGenerator
from POCL.POCLGenerator import POCLGenerator
from PlanParser import PlanParser
from tree_builder import TreeBuilder
from RuleGenerator import RuleGenerator
from MurTreeInputGenerator import MurTreeInputGenerator
from DataObjects.DecisionTree.RuleDecisionTree import RuleDecisionTree
from DataObjects.RuleGenerationDTO import RuleGenerationDTO
from Evaluator import Evaluator
from POCLRuleGenerator import POCLRuleGenerator

path = os.path.dirname(__file__)
path_temp = os.path.join(path,"temp")
output_folder = os.path.join(path,"DataHandler","Database")
#configure logger
now = datetime.now()
dt_str =now.strftime("%d_%m_%Y_%H_%M_%S")
log_path =os.path.join(path, "Log")
log_file_path = os.path.join(log_path, f"logfile_{dt_str}.log")
if not os.path.exists(os.path.join(log_path)):
    os.mkdir(log_path)


logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s %(name)s - %(levelname)s: %(message)s')
terminal_writter = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)s - %(levelname)s: %(message)s')
terminal_writter.setFormatter(formatter)
logging.getLogger("").addHandler(terminal_writter)
logger = logging.getLogger(__name__)

def run(load_from_file: bool, create_database: bool, end_time, dataset, problem_runs_folder :str,
        domain_name, treeDepth, max_node_count, use_pocl = True, use_bias=True, use_types=False, use_exsisting_rules = False):
    
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)

    if os.path.exists(path_temp):
        shutil.rmtree(path_temp)
    os.mkdir(os.path.join(path_temp))
    # Build dir path
    dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_path_split = dir_path.split("\\")
    dir_path = dir_path_split[0]
    # this is required for windows only and skipped on linux
    for i in range(1, len(dir_path_split)):
        dir_path += "\\" + dir_path_split[i]

    folder_path = os.path.join(dir_path, dataset, domain_name)

    # parse domain
    domain = PDDLDomain.from_pddl_file(os.path.join(folder_path, "domain.pddl"))
    db_handlerV2 = DatabaseHandlerV2(domain, False, create_database)

    # Generate negative and positive examples
    examples = []
    example_generator = ExampleGenerator()
    start_time = time.time()
    if not load_from_file:
        examples = example_generator.generat_problem_examples(os.path.join(folder_path, problem_runs_folder), domain)
    else:
        examples = example_generator.generate_from_file()
    logger.info("Example generation took: " + str((time.time() - start_time)) + "s")

    pddl_domain = parse_domain(os.path.join(folder_path, "domain.pddl"))
    pocl_gen = POCLGenerator(domain)
    start_time = time.time()
    graphs = []
    for problem in examples:
        db_handlerV2.insert_problem(problem)
        if use_pocl:
            graph = pocl_gen.generate_graph(problem)
            graph.problem = problem
            graphs.append(graph)
    logger.info("Database generation took: " + str((time.time() - start_time)) + "s")

    model_paths = []
    tree_paths = []
    model_info_strings = []
    model_info = {"":""}
    model_info.clear()
    pocl_rule_generator = None
    if use_pocl:
        pocl_rule_generator = POCLRuleGenerator(graphs, domain)
    for key, action in domain.actions.items():

        try:
            logger.info(f"Generating Rules for {key}")
            model_info["Action"] = key
            model_info["Dataset"] = problem_runs_folder
            rules_to_save_path = os.path.join(path,"generated_rules")
            rules_to_save_file_name = f"{domain_name}_{key}_{problem_runs_folder}_{end_time}.rdump"
            if not os.path.exists(rules_to_save_path):
                os.mkdir(rules_to_save_path)

            rules = []
            rule_num = 0
            rule_discarded_num = 0
            allEntries = db_handlerV2.fetch_all_action_id_entries(action)
            good_operators_cnt = db_handlerV2.get_good_operator_count(action)
            bad_operators_cnt = db_handlerV2.get_bad_operator_count(action)
            model_info["PositiveOperators"] = good_operators_cnt
            model_info["NegativeOperators"] = bad_operators_cnt

            logger.info("Positive operators number: {}, Negative operators number: {}".format(
                model_info["PositiveOperators"], model_info["NegativeOperators"]))

            murtree_input_generator : MurTreeInputGenerator = None
            tb = None
            rule_generator = None
            start_time = time.time()
            total_time = 0
            rule_gen_time = 0
            #restore rules generated previously
            if os.path.isfile(os.path.join(rules_to_save_path,rules_to_save_file_name)):
                logger.info("Restoring previously generedted rules")
                file = open(os.path.join(rules_to_save_path, rules_to_save_file_name), 'rb')
                rule_dto : RuleGenerationDTO = pickle.load(file)
                tb = rule_dto.tree_builder
                murtree_input_generator = rule_dto.murtree_input_generator
                rule_generator = rule_dto.rule_generator
                rules = rule_dto.rules
                rule_num = rule_dto.rule_count
                rule_discarded_num = rule_dto.discarded_rule_count
                total_time = rule_dto.total_time
                rule_gen_time = rule_dto.rule_gen_time
            else:
                logger.info("No existing rule generation found, starting to generate new rules")
                murtree_input_generator = MurTreeInputGenerator(allEntries)
                if use_pocl:
                    logger.info("Using POCL as rule engine")
                    temp_rules = pocl_rule_generator.generate_rules(action, 2000, end_time)
                    rule_gen_time = time.time() - start_time
                    last_log = time.time()
                    rule_eval_cnt = 0
                    rule_eval_state_time = time.time()
                    logger.info(f"Evaluation rules: {len(temp_rules)}")
                    for rule in temp_rules:
                        #if evaluation takes more then 30mins just contiune with the once done
                        if time.time() - rule_eval_state_time > 30*60:
                            break

                        if time.time() - last_log >= 30:
                            logger.info(f"Evaluation rules reached {rule_eval_cnt} of {len(temp_rules)}")
                            last_log = time.time()

                        rows_accepted = db_handlerV2.fetch_rows_accepted_by_rule(rule, rule_num)
                        if len(rows_accepted) > 0:
                            rules.append(rule)
                            murtree_input_generator.update_dictionary_values(rows_accepted)
                            rule_num += 1
                        else:
                            rule_discarded_num += 1
                        rule_eval_cnt += 1
                else:
                    logger.info("Using Tree Builder as rule engine")
                    tb = TreeBuilder(domain, action, use_bias, use_types)
                    rule_generator = RuleGenerator(tb)
                    


                    while time.time() - start_time < end_time:
                        rule = rule_generator.next()
                        rule_generator.AnalyzeRule(rule, domain)
                        rows_accepted = db_handlerV2.fetch_rows_accepted_by_rule(rule, rule_num)
                        if len(rows_accepted) > 0:
                            rules.append(rule)
                            murtree_input_generator.update_dictionary_values(rows_accepted)
                            rule_num += 1
                            rule_generator.expand()
                        else:
                            rule_discarded_num += 1
                    rule_gen_time = time.time() - start_time
                
                t_total_time = time.time() - start_time
                logger.info(f"Rule and eval took {t_total_time}s")
                #dumped generated rules such it can be fetched at a later point
                rule_to_save = RuleGenerationDTO(None, None, murtree_input_generator, rules, rule_num, rule_discarded_num, t_total_time, rule_gen_time)
            
                logger.info(f"Writing generated rules to: {rules_to_save_file_name}")
                file = open(os.path.join(rules_to_save_path, rules_to_save_file_name), 'ab')
                pickle.dump(rule_to_save, file)
                file.close()

            logger.info(f"Done generating Rules for {key} usable count: {rule_num}, discarded: {rule_discarded_num} total: {rule_num+rule_discarded_num}")
            model_info["RuleGenerationTime"] = rule_gen_time
            model_info["TotalRules"] = rule_num+rule_discarded_num
            model_info["UsedRules"] = rule_num
            if rule_num <= 0:
                logger.info(f"no rules was generated for {key} skipping to next action")
                continue
            

            logger.info(f"Generating murtree for {key}")
            #murtree_input_generator.dump_to_file(path_temp, action.name)
            mur_tree_input = murtree_input_generator.generate_murtree_input()
            tree_output_path = os.path.join(output_folder, f"decision_tree_{key}.txt")
            rule_decision_tree = None
            try:
                murtree_time = time.time()
                model_info["TreeTime"] = 0
                rule_decision_tree = MurTreeGenerator.generate(mur_tree_input, tree_output_path, 120*60, treeDepth, max_node_count, action)
                model_info["TreeTime"] = round(time.time() - murtree_time, 3)
                logger.info("generate tree took {}s".format(model_info["TreeTime"]))
                if os.path.exists(tree_output_path) and rule_decision_tree != None:
                    tree_paths.append(tree_output_path)
                else:
                    raise Exception("Tree file missing or rule_decision_tree is none")
            except Exception as e:
                logger.error(f"generate tree failed in {time.time() - murtree_time}s -- {e}")
                continue
            
            
            logger.info(f"Generating ruleDecisionTree for {key}")
            #rule_decision_tree = RuleDecisionTree(Streed_Tree, action)
            rule_list = rule_decision_tree.rule_list
            model_info["RulesInTree"] = len(rule_list)
            logger.info("Generate rule to SQL schemas for {} for {} rules".format(key,model_info["RulesInTree"]))
            rules_in_tree = []
            for rule_num in rule_list:
                rules_in_tree.append((rule_num, rules[rule_num]))
            query_dict = db_handlerV2.build_rules_to_sql_schema(rules_in_tree)

            if False:
                #Log rules in tree to csv
                rule_csv_file = open(os.path.join(output_folder,f"{key}_rules.csv"),"w")
                rule_csv_file.write("ruleNumber;rule;SQL\n")
                for rule_tuple in rules_in_tree:
                    rule_csv_file.write("{};{};{}\n".format(rule_tuple[0], rule_tuple[1], query_dict[rule_tuple[0]]))
                rule_csv_file.close()

            logger.info(f"Filling ruleDecisionTree for {key} with SQL schemas")
            rule_decision_tree.fill(query_dict)
            
            #total_time is either 0 when rule generation has run otherwise its
            #the time the restored rules gen time is
            model_info["Time"] = round((time.time() - start_time) + total_time, 3)

            logger.info(f"Saving model for {key}")
            file_name = f"model_{domain.name}_{action.name}.rulemodel"
            model_path_out = os.path.join(path, "DataHandler", "Database", file_name) 
            logger.info(f"Saving model: {file_name}")
            file = open(model_path_out, 'ab')
            pickle.dump(rule_decision_tree, file)
            file.close()

            model_info["TreeDepth"] = treeDepth
            model_info["MaxNodeCount"] = max_node_count

            model_info_line =""
            for dict_key, value in model_info.items():
                model_info_line += f"{value},"
            model_info_line = model_info_line.removesuffix(",")
            model_info_strings.append(f"{model_info_line}\n")

            model_paths.append(model_path_out)
        except Exception as e:
            logger.error(f"Learning model for {key} failed, --- {e}")

    db_handlerV2.db_connection.close()
    

    logger.info(f"Prepare files for tar, {domain_name}")
    #prepare model files for tar
    result_path = os.path.join(path, "TrainedModels",f"incumbents_{domain.name}_{problem_runs_folder}_{end_time}_{treeDepth}_{max_node_count}")
    if os.path.exists(result_path):
        shutil.rmtree(result_path)
    if not os.path.exists(result_path):
         os.makedirs(result_path)
    
    for file in os.listdir(output_folder):
        if file.endswith(".csv"):
            shutil.copy(os.path.join(output_folder,file), result_path)

    for m_path in model_paths:
        shutil.copy(m_path, result_path)
    for t_path in tree_paths:
        shutil.copy(t_path, result_path)
    
    csv_desc = ""
    for key, value in model_info.items():
        csv_desc += f"{key},"
    csv_desc = csv_desc.removesuffix(",")

    csv_file = open(os.path.join(result_path,"model_run_info.csv"),"w")
    csv_file.write(f"{csv_desc}\n")
    csv_file.writelines(model_info_strings)
    csv_file.close()

    logger.info(f"Prepare config file for tar, {domain_name}")
    #prepare config file for tar
    config_file_content = '''{\"alias\": \"lama-first\", \"ignore-bad-actions\": \"true\", 
    \"queue_type\": \"ipc23-single-queue\", \"termination-condition\": \"full\", \"num_bad_rules\": 3, \"num_good_rules\": 5}'''
    config_file_path = os.path.join(result_path, "config")
    if os.path.exists(config_file_path):
        os.remove(config_file_path)
    config_file = open(config_file_path, 'a+')
    config_file.write(config_file_content)
    config_file.close()
    
    logger.info(f"Compressing models to tar, {domain_name}")
    #compress required files for GOFAI
    with tarfile.open(os.path.join(result_path,"domain_knowledge.dk"), "w:gz") as tar:
                tar.add(result_path, arcname=os.path.sep)

    logger.info(f"Training model for {domain_name} completed")

def run_planner(domain_path: str, problem_path: str, model_path: str, plan_output_path):
    #if not os.path.exists(plan_output_path):
     #   os.mkdir(plan_output_path)

    sys.argv.clear()
    sys.argv.append(__file__)
    sys.argv.append(model_path)  # path to domain knowledge file
    sys.argv.append(domain_path)  # path to domain file
    sys.argv.append(problem_path)  # path to problem file
    sys.argv.append(plan_output_path)  # path to output plan file
    plan.main()


def generate_dataset2(data_folder:str, total, training_ratio, domains_to_generate, reset = False):
    training_ratio_precent = int(training_ratio * 100)
    if len(domains_to_generate) > 0:
        domains = domains_to_generate
    else:
        domains = os.listdir(data_folder)

    output_folder = os.path.join(path, "Data", "autoscale-learning")
    if reset and os.path.exists(output_folder):
        shutil.rmtree(output_folder)
        os.makedirs(output_folder)
    elif not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    for domain in domains:
        tasks_path = os.path.join(data_folder, domain, "good-operators-unit")
        output_domain_folder = os.path.join(output_folder,domain)
        output_test_folder = os.path.join("TestingData", "autoscale-learning", domain)
        all_task_folder = os.path.join(output_domain_folder,"training")
        
        if not os.path.exists(all_task_folder):
            os.makedirs(all_task_folder)
            shutil.copy(os.path.join(data_folder,domain,"tasks","domain.pddl"),output_domain_folder)
            for folder in os.listdir(tasks_path):
                source = os.path.join(tasks_path, folder)
                dst = os.path.join(all_task_folder,folder)
                if os.path.isfile(os.path.join(source,"all_operators")) and os.path.isfile(os.path.join(source,"good_operators")):
                    os.mkdir(dst)
                    shutil.copy(os.path.join(source,"problem.pddl"), os.path.join(dst,"problem.pddl"))
                    shutil.copy(os.path.join(source,"all_operators"), os.path.join(dst,"all_operators"))
                    shutil.copy(os.path.join(source,"good_operators"), os.path.join(dst,"good_operators"))
                    shutil.copy(os.path.join(source,"domain.pddl"), os.path.join(dst,"domain.pddl"))
                    shutil.copy(os.path.join(source,"sas_plan"), os.path.join(dst,"sas_plan"))
                else:
                    continue
                #shutil.copytree(tasks_path, all_task_folder)
        
        tasks = os.listdir(all_task_folder)
        total_task_count = len(tasks)

        
        if total > 0:
            if total < total_task_count:
                total_task_count = total

      
        data_set_training_folder_path = os.path.join(output_domain_folder,f"training_{total}_{training_ratio_precent}")
        data_set_tasks_training_folder_path = os.path.join(output_domain_folder,f"tasks_training_{total}_{training_ratio_precent}")
        data_set_tasks_testing_folder_path = os.path.join(output_domain_folder,f"tasks_testing_{total}_{training_ratio_precent}")
        data_set_testing_folder_path = os.path.join(output_test_folder,f"testing_{total}_{training_ratio_precent}")

        if os.path.exists(data_set_training_folder_path):
            shutil.rmtree(data_set_training_folder_path)
        if os.path.exists(data_set_testing_folder_path):
            shutil.rmtree(data_set_testing_folder_path)
        if os.path.exists(data_set_tasks_training_folder_path):
            shutil.rmtree(data_set_tasks_training_folder_path)
        if os.path.exists(data_set_tasks_testing_folder_path):
            shutil.rmtree(data_set_tasks_testing_folder_path)

        os.makedirs(data_set_training_folder_path)
        os.makedirs(data_set_testing_folder_path)
        os.makedirs(data_set_tasks_training_folder_path)
        os.makedirs(data_set_tasks_testing_folder_path)
        shutil.copy(os.path.join(data_folder,domain,"tasks","domain.pddl"), os.path.join(data_set_tasks_training_folder_path,"domain.pddl"))
        shutil.copy(os.path.join(data_folder,domain,"tasks","domain.pddl"), os.path.join(data_set_tasks_testing_folder_path,"domain.pddl"))
        

        training_count = int(total_task_count * training_ratio)
        testing_count = int(total_task_count * (1 - training_ratio))

        while(training_count > 0):
            idx = random.randint(0, len(tasks)-1)
            shutil.copytree(os.path.join(all_task_folder,tasks[idx]), os.path.join(data_set_training_folder_path,tasks[idx]))
            shutil.copy(os.path.join(all_task_folder,tasks[idx],"problem.pddl"), os.path.join(data_set_tasks_training_folder_path,f"{tasks[idx]}.pddl"))
            tasks.remove(tasks[idx])
            training_count -= 1
        
        while testing_count > 0:
            idx = random.randint(0, len(tasks)-1)
            shutil.copytree(os.path.join(all_task_folder, tasks[idx]), os.path.join(data_set_testing_folder_path, tasks[idx]))
            shutil.copy(os.path.join(all_task_folder,tasks[idx],"problem.pddl"), os.path.join(data_set_tasks_testing_folder_path,f"{tasks[idx]}.pddl"))
            tasks.remove(tasks[idx])
            testing_count -= 1
        shutil.copy(os.path.join(output_domain_folder,"domain.pddl"),data_set_testing_folder_path)


def generate_dataset(problem_count:int, out_folder_name:str):
    domain_folder = os.path.join(path,"Data","IPC")
    domains = os.listdir(domain_folder)
    for domain in domains:
        dataset_folder = os.path.join(domain_folder,domain,"training")
        runs = os.listdir(dataset_folder)
        runs.sort()
        #Validate runs
        valid_runs = []
        for run in runs:
            run_files = os.listdir(os.path.join(dataset_folder, run))
            if "all_operators" in run_files and "good_operators" in run_files and "problem.pddl" in run_files:
                valid_runs.append(run)

        output_training_folder = os.path.join(domain_folder, domain, out_folder_name)
        if os.path.exists(output_training_folder):
            shutil.rmtree(output_training_folder)
        
        select_cnt = range(0, len(valid_runs))  
        if problem_count > 0 and problem_count < len(valid_runs):
            valid_runs.reverse()
            select_cnt = range(0, problem_count)

        for num in select_cnt:
            run = valid_runs[num]
            run_folder = os.path.join(dataset_folder,run)
            shutil.copytree(run_folder, os.path.join(output_training_folder, run))
    

def main(): 
    logging.info("------------Model learning started---------------")
    domain = "floortile"
    load_from_file = False
    create_database = True
    use_types = False
    use_bias = False
    use_pocl = True
    training_sets = ["training10", "training30", "training_full"]
    training_sets = ["training_full"]
    training_sets = ["training_200_70"]
    data_set = os.path.join("Data", "IPC")
    data_set = os.path.join("Data", "autoscale-learning")
    time_limites = [1*60]
    tree_depth = [3, 4]
    tree_Max_node_count = [7, 15]

    #domains_to_generate_data = ["blocksworld", "floortile", "rovers"]
    #domains_to_generate_data = ["floortile"]
    #generate_dataset2("/home/p10/Downloads/autoscale-learning-main/data/", 200, 0.7, [])
    #run(load_from_file, create_database, 2, data_set, training_sets[0], domain, 3, 7, use_pocl, use_bias, use_types)
    #Evaluator.evaluator([])
    #domain = "transport"
    #run(load_from_file, create_database, 60, data_set, training_sets[2], domain, 3, 7, use_pocl, use_bias, use_types)
    #domain = "satellite"
    #run(load_from_file, create_database, 60, data_set, training_sets[2], domain, 3, 7, use_pocl, use_bias, use_types)
    #domain = "ferry"
    #run(load_from_file, create_database, 60, data_set, training_sets[2], domain, 3, 7, use_pocl, use_bias, use_types)

    #Evaluator.evaluator(["rover", "transport", "spanner", "satellite", ""])
    #Evaluator.evaluator([])
    #domains = ["spanner","transport"]
    #domains = domains_to_generate_data

    domains = os.listdir(data_set)
    domains = ["barman","blocksworld","depots","floortile","gripper","rover","satellite","zenotravel"]
    for domain in domains:
        if domain == "blocksworld":
            use_types = False
        else:
            use_types = True

        for t_limit in time_limites:
            for training_set in training_sets:
                logger.info(f"----------------Training for {domain}, time: {t_limit}, Dataset: {data_set}, trainingset{training_set}, Tree depth: {3}, Max node count: {7} ----------------")
                try:
                    run(load_from_file, create_database, t_limit, data_set, training_set, domain, 3, 7, use_pocl, use_bias, use_types)
                except Exception as e:
                    logger.error(f"Failed training for {domain}, time: {t_limit}, Dataset: {data_set} - {e}")
        
    default_result_folder = os.path.join(path,"result")
    domain_path = os.path.join(path, "Data", "IPC", domain, "domain.pddl")
    problem_path = os.path.join(path, "Data", "IPC", domain, "testing", "easy", "p01.pddl")
    model_path = os.path.join(path, "TrainedModels", "incumbents_childsnack_training10_10_3_7", "domain_knowledge.dk")
    sas_plan_output_path = os.path.join(default_result_folder, domain, "plans", "p0.sas")

    if os.path.exists(default_result_folder):
        shutil.rmtree(os.path.join(default_result_folder, domain))
    if not os.path.exists(default_result_folder):
        os.mkdir(default_result_folder)
    os.mkdir(os.path.join(default_result_folder, domain))
    os.mkdir(os.path.join(default_result_folder, domain,"plans"))


    #run_planner(domain_path, problem_path, model_path, sas_plan_output_path)


# Using the special variable  
# __name__ 
if __name__ == "__main__":
    main()

# sys.argv.append(defaultFolder + domain +"/domain_knowledge.dk")#path to domain knowledge file
#    sys.argv.append(defaultFolder + domain + "/domain.pddl")#path to domain file
#    sys.argv.append(defaultFolder + domain + "/problems/" + problem)#path to problem file
#    sys.argv.append(defaultFolder + domain + "/plans/"+ problem.split('.')[0] +".sas")#path to output plan file


# run_planner(domain_path, problem_path, model_path, sas_plan_output_path)

# run_eval(path + "\\data\\blocksworld\\domain.pddl", path + "\\data\\blocksworld\\testing\\hard\\p30.pddl", path + "\\DataHandler\\Database\\")


