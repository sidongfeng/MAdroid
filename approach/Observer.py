import argparse
import pprint
import re
from time import sleep

import xmltodict

from utils.base_utils import llm
from utils.base_utils import memory
from utils.base_utils.android_controller import ActionType
from utils import observer_utils
from Operator import ReturnData
import Coordinator
from utils import operator_utils


system_prompt = "You are a helpful mobile testing assistant."


class Observer_agent:
    def __init__(self):
        self.overview_task = ""
        self.device_type_list = []
        self.sub_task_list = []
        self.is_info1_ok = False
        self.llm = llm.GeneralGPT()
        self.messages = [{"role": "system", "content": system_prompt}]

        self.last_action = ""
        self.last_summary = ""

        self.observer_skip_flag = False
        self.observer_response = ""

        self.count = 0

        self.t_list = []

    def align1(self, overview_task: str, device_type_list: list, sub_task_list: list):
        self.overview_task = overview_task
        self.device_type_list = device_type_list
        self.sub_task_list = sub_task_list
        self.is_info1_ok = True

    def assess(self, current_device_num: int, all_comps: str, memory_list: list, t_ob: list):
        if len(memory_list) == 0:
            return
        self.messages = [{"role": "system", "content": system_prompt}]
        print("\nObserver: Observer is running....")
        prompt = observer_utils.ob_prompt1 + observer_utils.ob_prompt2(self.overview_task, self.device_type_list, current_device_num, self.sub_task_list)
        if self.t_list:
            prompt += observer_utils.ob_prompt_test(self.t_list, current_device_num, all_comps)
        else:
            prompt += observer_utils.ob_prompt3(memory_list, current_device_num, all_comps)
        t_ob[0] = prompt

        prompt = prompt.replace("favorite", "favrite").replace("Favorite", "Favrite")
        new_message = {"role": "user", "content": prompt}
        self.messages.append(new_message)

        result = self.llm.ask_gpt_message(messages=self.messages)

        self.messages = [{"role": "system", "content": system_prompt}]
        print("\n-----------")
        print(result)
        print("-----------\n")
        return result['content'].splitlines()[-1]

    def assess_device_switch(self, current_device_num: int, memory_list: list, matches_list: list, sub_messages: list,
                             all_comps: str):
        print("Observer is assessing whether the device should be switch...")
        prompt = observer_utils.observer_prompt_device_switch(self.app_name, self.overview_task, self.device_type_list,
                                                              current_device_num, memory_list, matches_list,
                                                              sub_messages,
                                                              all_comps)
        new_message = {"role": "user", "content": prompt}
        self.messages.append(new_message)

        # pprint.pprint(self.messages)

        result = self.llm.ask_gpt_message(messages=self.messages)

        self.messages = [{"role": "system", "content": system_prompt}]
        print("\n-----------")
        print(result)
        print("-----------\n")
        return result['content']

    def assess_task_done(self, current_device_num: int, memory_list: list, task_done_summary: str, sub_messages: list,
                         all_comps: str):
        print("Observer is assessing whether the task is over...")
        prompt = observer_utils.observer_prompt_task_done(self.app_name, self.overview_task, self.device_type_list,
                                                          current_device_num, memory_list, task_done_summary,
                                                          sub_messages, all_comps)
        new_message = {"role": "user", "content": prompt}
        self.messages.append(new_message)
        result = self.llm.ask_gpt_message(messages=self.messages)
        self.messages = [{"role": "system", "content": system_prompt}]
        print("\n-----------")
        print(result)
        print("-----------\n")
        return result['content']

    def page_abstract(self, activity_name: str, pre_activity_name: str, pre_action: str, all_comps: str):
        print("\nObserver: Current screen is abstracting...")
        abstract_system_prompt = ("I want you to act as a UI page summarizer. I will provide you with a screen of a "
                                  "mobile app, and your task is to summarize it. The information I will provide "
                                  "includes the app's name, the activity_name of the screen, and the names "
                                  "of all the components on that screen. Your goal is to summarize the content and "
                                  "functionality of the screen in a brief two to three sentences.")
        mes = [{"role": "system", "content": abstract_system_prompt}]
        prompt = f"This is a app named {self.app_name}. The current screen is named: '{activity_name}'. "
        if pre_activity_name != "":
            prompt += f"And it is reached from screen '{pre_activity_name}' through action '{pre_action}'"
        prompt += f"\nHere is the elements on current screen '{activity_name}': \n"
        prompt += all_comps
        prompt += "\nI want you to summarize this screen in a brief two to three sentences."
        new_message = {"role": "user", "content": prompt}
        mes.append(new_message)
        res = self.llm.ask_gpt_message(messages=mes)
        return res['content']

    def expand(self, device_type_list: list):
        self.device_type_list = device_type_list
        t_dict = {"history_screen": [],
                  "history_action": [],
                  "activity": []}
        self.sub_messages.append(t_dict)

    # j_flag, represents the type identified by the observer.
    # all_comps, components on current screen (after last action from action list).
    # matches, content from operator.
    def run_observer(self, j_flag: int, device_id: int, all_comps: str, pool: memory.MemoryPool):
        # if len(self.sub_messages[device_id-1].get("history_action")) == 0:
        #     response = {"action_infos": [{}], "status": 0, "device_switch": False, "task_done": False}
        #     return ReturnData(0, 0, response)
        if self.observer_skip_flag:
            self.observer_skip_flag = False
            response = {"action_infos": [{}], "status": 0, "device_switch": False, "task_done": False}
            return ReturnData(0, 0, response)

        if j_flag == 0 and self.count != 2:
            self.count += 1
            response = {"action_infos": [{}], "status": 0, "device_switch": False, "task_done": False}
            return ReturnData(0, 0, response)
        elif self.count == 2:
            self.count = 0

        t_ob = [""]
        assess_result = self.assess(device_id, all_comps, pool.memory_pool_list, t_ob)

        if assess_result is None:
            response = {"action_infos": [{}], "status": 0}
            return ReturnData(0, 0, response)

        match_list = re.findall(r"'([^']*)'", assess_result)
        if len(match_list) == 5 and match_list[0] == "yes":

            if j_flag != 0:
                pool.memory_pool_list.pop()

            # self.observer_judge_flag = True
            self.observer_response = match_list[4]
            if match_list[2] == "yes":
                resp = {"action_infos": [
                    {"react": 3, }], "status": 0, "observer_response": self.observer_response}
                self.observer_response = ""
                return ReturnData(0, 0, resp)
            elif match_list[3] == "yes":
                resp = {"action_infos": [{"react": 2}], "status": 0, "observer_response": self.observer_response}
                self.observer_response = ""
                return ReturnData(0, 0, resp)
            resp = {"action_infos": [{"react": 1}], "status": 0, "observer_response": self.observer_response}
            self.observer_response = ""
            return ReturnData(0, 0, resp)
        # if j_flag == 1:
        #     assess_special_operation_result = self.assess_device_switch(device_id, pool.memory_pool_list,
        #                                                                 matches, self.sub_messages,
        #                                                                 all_comps)
        #     assess_matches = re.findall(r"'(.*?)'", assess_special_operation_result)
        #     if assess_matches[0] == 'no':
        #         self.remove_action_list_last_item(device_id)
        #         self.remove_screen_history_last_item(device_id)
        #         # self.device_switch_flag = True
        #         self.observer_response = assess_matches[1]
        #         self.observer_skip_flag = True
        #         # self.wrong_flag = True
        #         response = {
        #             "action_infos": [{"action_type": ActionType.NOP,
        #                               "action_list": self.sub_messages[device_id - 1]["history_action"]}],
        #             "status": 0, "observer_response": self.observer_response, "device_switch": False}
        #         self.observer_response = ""
        #         return ReturnData(0, 0, response)
        #     else:
        #         response = {"action_infos": [{}], "status": 0, "device_switch": True}
        #         return ReturnData(0, 0, response)
        # if j_flag == 2:
        #     assess_task_done_result = self.assess_task_done(device_id, pool.memory_pool_list, matches[1],
        #                                                     self.sub_messages, all_comps)
        #     assess_matches = re.findall(r"'(.*?)'", assess_task_done_result)
        #     if assess_matches[0] == "yes":
        #         response = {"action_infos": [{}], "status": 1, "task_done": True}
        #         return ReturnData(0, 0, response)
        #     else:
        #         # self.task_not_done_flag = True
        #         self.observer_response = assess_matches[1]
        #         self.observer_skip_flag = True
        #         print("Observer: Task haven't been completed yet.")
        #
        #         self.remove_action_list_last_item(device_id)
        #         self.remove_screen_history_last_item(device_id)
        #
        #         response = {"action_infos": [{"action_type": ActionType.NOP}], "status": 0,
        #                     "observer_response": self.observer_response,
        #                     "task_done": False}
        #         self.observer_response = ""
        #         return ReturnData(0, 0, response)
        response = {"action_infos": [{}], "status": 0}
        return ReturnData(0, 0, response)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", help="task's description")
    parser.add_argument("--dnum", help="The number of devices required for the task")
    parser.add_argument("--deviceid", help="Current device's id, like '1', '2'.")
    parser.add_argument("--historyInfo", help="history file of the task")
    parser.add_argument("--currentXml", help="Xml file path.")
    args = parser.parse_args()
    task = args.task
    d_num = args.dnum
    dtype = []
    sub_task_list = []
    device_id = int(args.deviceid)
    history_path = args.historyInfo
    xml_path = args.currentXml

    memory_pool = memory.MemoryPool()
    coordinator = Coordinator.Coordinator_agent(task)
    observer = Observer_agent()
    observer.align1(task, dtype, sub_task_list)

    for i in range(len(d_num)):
        dtype.append("default user")
        sub_task_list.append("")

    coordinator.task_create(d_num, [], memory_pool)

    try:
        with open(xml_path, 'r') as file:
            content = file.read()
    except FileNotFoundError:
        print("File not exist.")
    except IOError:
        print("Can not open file.")

    try:
        with open(history_path, 'r') as file:
            history_info = file.read()
    except FileNotFoundError:
        print("File not exist.")
    except IOError:
        print("Can not open file.")

    line_list = history_info.splitlines()
    for line in line_list:
        if '### Thought ###' in line:
            observer.t_list.append(line)
        else:
            observer.t_list[-1] = observer.t_list[-1] + f"\n{line}"

    memory_pool.memory_pool_list.append("")

    xml = content
    if "<hierarchy rotation=" in xml:
        align_xml = xml
    else:
        align_xml = operator_utils.xml_align(xml)
    xml_dict = xmltodict.parse(align_xml)
    all_comps = operator_utils.getMergedComponents(xml_dict)
    t_list = []
    operator_utils.component_prompt(str(device_id), all_comps, t_list)

    o_result = observer.run_observer(1, device_id, t_list[0], memory_pool)


