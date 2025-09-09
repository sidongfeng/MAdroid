import argparse
import random
import re
import threading
from time import sleep

import xmltodict
import uiautomator2 as u2

from utils.base_utils import android_controller
from utils.base_utils.android_controller import ActionType
from utils import operator_utils
from utils.base_utils import llm
from utils.base_utils import memory
from utils import mes_compress_agent
from utils import text_generate_agent

task_done = False


class ReturnData:
    def __init__(self, data_type: int, device_switch: int, response: dict):
        self.data_type = data_type
        # data_type: 0 normal for task execute; 1 switch device; 2 normal for task create
        self.device_switch = device_switch
        self.response = response


class Operator_agent:
    # The device_id starts from 1, where the execute_state of the first device is 0, and the execute_state of other
    # devices is 1.
    def __init__(self, device_id, execute_state):
        self.llm = llm.GeneralGPT()
        self.compression_agent = mes_compress_agent.Message_compression_agent()
        self.device_id = device_id
        self.execute_state = execute_state

        # The above variables are assigned values in the task_create phase.
        self.overview_task = ""
        self.device_total_num = 1
        self.device_type_list = []
        self.device_ip_list = []
        self.messages = []
        self.device_sub_task_list = []
        self.pre_xml = " "

        self.last_summary = ""
        self.last_action = ""
        self.t_list = []
        self.observer_judge_flag = False
        self.task_not_done_flag = False
        self.device_switch_flag = False
        self.observer_reason = ""

    # Synchronize the information of each operator.
    def task_info_align(self, m_pool: memory.MemoryPool):

        if m_pool.is_info1_ok:
            self.overview_task = m_pool.overview_task
            self.device_type_list = m_pool.device_type_list
            self.device_ip_list = m_pool.device_ip_list

        if m_pool.is_info2_ok:
            self.device_total_num = m_pool.device_total_num
            self.device_sub_task_list = m_pool.device_sub_task_list

    def task_execution(self, execute_info: dict, pool: memory.MemoryPool):
        e_prompt = ""  # Prompt for the agent's first run.
        input_task = ""  # Store specified tasks for text input.

        xml = execute_info.get("xml")
        if "<hierarchy rotation=" in xml:
            align_xml = xml
        else:
            align_xml = operator_utils.xml_align(xml)
        xml_dict = xmltodict.parse(align_xml)
        activity = execute_info.get("activity")
        all_components = operator_utils.getMergedComponents(xml_dict)
        # memory_message_list = pool.memory_pool_list

        if pool.current_device != self.device_id:
            response = {"action_infos": [{"action_type": android_controller.ActionType.NOP}], "status": 0}
            return ReturnData(0, 0, response)

        # Initialization of the prompt for the current agent.
        if self.execute_state == 1:
            if not pool.is_info1_ok:
                print("Device {}: Coordinator has not yet completed its task.".format(self.device_id))
                response = {"action_infos": [{"action_type": android_controller.ActionType.NOP}], "status": 0}
                return ReturnData(0, 0, response)
            self.task_info_align(pool)
            self.messages = [{'system': 'You are a helpful AI mobile testing assistant.'}]
            action_list = pool.get_device_actions(self.device_id)
            e_prompt += operator_utils.prompt1 + operator_utils.prompt2(self.device_sub_task_list, self.overview_task,
                                                                        self.device_type_list, self.device_id,
                                                                        action_list)

            self.t_list = []
            e_prompt += operator_utils.prompt3(activity, all_components, self.t_list) + operator_utils.last_prompt_template
            self.execute_state = 2

        # Task execution phase.
        if self.execute_state == 2:
            self.execute_state = 1
            if e_prompt != "":
                prompt = e_prompt
            else:
                action_list = pool.get_device_actions(self.device_id)
                prompt = operator_utils.re_prompt1(activity, all_components, self.device_sub_task_list, self.overview_task,
                                                   self.device_type_list, self.device_id, action_list, self.t_list)

            if self.observer_judge_flag:
                prompt += (
                    f"\n## Additional Info:\n Our last action was considered wrong, and here is the reason: \n\"{self.observer_reason}\"\n"
                    f"Maybe we can choose another action this time.")
                self.observer_judge_flag = False
                self.observer_reason = ""
            if self.task_not_done_flag:
                prompt += ("\n## Additional Info:\nOur last action was 'Task done', but maybe it is not the right time to end all tasks? "
                           "And here is the reason:\n\"{}\"\n"
                           "Please double-check to see if all devices have completed their tasks. Please refer to the "
                           "previously mentioned overview_task. If other devices have not completed their tasks, "
                           "switch to another device. If you still have unfinished tasks, please continue completing "
                           "them.").format(self.observer_reason)
                self.task_not_done_flag = False
                self.observer_reason = ""
            if self.device_switch_flag:
                prompt += ("\n## Additional Info:\nOur last action was 'Switch to device...', but maybe it is not the right operation? And "
                           "here is the reason:\n\"{}\"\n"
                           "Please double-check to see if all your task has done. Please refer to the previously "
                           "mentioned overview_task. If you still have unfinished tasks, please continue completing "
                           "them.").format(self.observer_reason)
                self.device_switch_flag = False
                self.observer_reason = ""

            # print(prompt)
            prompt = prompt.replace("favorite", "favrite").replace("Favorite", "Favrite")
            operator_utils.ad_new_mes(self.messages, prompt)
            result = self.llm.ask_gpt_message(messages=self.messages)

            # print(result)

            print("\n" + f"Device {self.device_id}: " + result['content'])

            self.last_action = result['content'].splitlines()[-1]
            self.last_summary = result['content'].split('###')[2]

            result['content'] = result['content'].replace("favorite", "favrite")
            self.messages.append(result)
            matches = re.findall(r"'(.*?)'", self.last_action)
            if matches[0].lower() == "tap":
                target_text = matches[1]
                target_list = []
                for item in all_components:
                    if '@text' in item and item['@text'] == target_text:
                        target_list = [item]
                        break
                    elif '@text' in item and target_text in item['@text']:
                        target_list.append(item)
                    elif item['@content-desc'] == target_text or target_text in item['@content-desc']:
                        target_list.append(item)
                    elif item['@resource-id'] == target_text or target_text in item['@resource-id']:
                        target_list.append(item)
                if len(target_list) != 0:
                    target = random.choice(target_list)
                    response = {
                        "action_infos": [{
                            "action_type": android_controller.ActionType.CLICK,
                            "bounds": [int(num) for substring in target['@bounds'].strip("[]").split("][") for num in
                                       substring.split(",")],
                            "resource_id": target['@resource-id'],
                            "class": target['@class'],
                            "text": target['@content-desc'],
                            "throttle": 500
                        }],
                        "status": 0, "matches": matches
                    }
                    pool.add_memory("0", self.device_id, self.last_action, self.last_summary)
                    return ReturnData(0, 0, response)
                else:
                    print("Device {}: Wrong component selected.".format(self.device_id))
                    response = {"action_infos": [{"action_type": android_controller.ActionType.NOP}], "status": 0, "matches": matches}
                    return ReturnData(0, 0, response)
            elif len(matches) > 0 and matches[0] == 'Switch to input generation':
                pool.add_memory("0", self.device_id, self.last_action, self.last_summary)
                if len(matches) == 1:
                    self.execute_state = 3
                elif len(matches) == 2:
                    self.execute_state = 4
                    input_task = matches[1]
            elif matches[0] == 'nop':
                pool.add_memory("0", self.device_id, self.last_action, self.last_summary)
                response = {"action_infos": [{"action_type": android_controller.ActionType.NOP}], "status": 0,
                            "matches": matches}
                return ReturnData(0, 0, response)
            elif matches[0] == 'back':
                pool.add_memory("0", self.device_id, self.last_action, self.last_summary)
                response = {"action_infos": [{"action_type": android_controller.ActionType.BACK}], "status": 0,
                            "matches": matches}
                return ReturnData(0, 0, response)
            elif len(matches) > 0 and matches[0].startswith("Switch to device"):
                pool.current_device = int(re.search(r'\d+', matches[0]).group())
                pool.add_memory("1", self.device_id, self.last_action, matches[1])

                if pool.current_device > int(pool.device_total_num):
                    response = {"action_infos": [{"action_type": android_controller.ActionType.ACTIVATE}], "status": 0}
                else:
                    response = {"action_infos": [{"action_type": android_controller.ActionType.NOP}], "status": 0, "device_switch": True, "matches": matches}
                return ReturnData(0, 0, response)
            elif len(matches) > 0 and matches[0] == 'Task done':
                pool.add_memory("1", self.device_id, self.last_action, self.last_summary)
                response = {"action_infos": [{}], "status": 1, "matches": matches}
                return ReturnData(0, 0, response)

        if self.execute_state == 3:
            input_agent = text_generate_agent.Text_generate_agent("")
            data_action = {"xml": xml, "activity": activity, "type": 1}
            result = input_agent.input_generate(data_action, 0, "")
            self.execute_state = 1
            result.response["matches"] = []
            return result

        if self.execute_state == 4:
            input_agent = text_generate_agent.Text_generate_agent("")
            data_action = {"xml": xml, "activity": activity, "type": 1}
            result = input_agent.input_generate(data_action, 1, input_task)
            self.execute_state = 1
            result.response["matches"] = []
            return result

    # def remove_action_list_last_item(self):
    #     del self.action_list[-1]


# result_queue = queue.Queue()


def task_execute(i: int, controller_dict: dict):
    global task_done
    while not task_done:
        xml = controller_dict.get("d{}".format(i + 1)).dump_hierarchy(compressed=False, pretty=False)
        activity = controller_dict.get("d{}". format(i +1)).app_current().get("activity").split("/")[-1]

        memory_pool = controller_dict.get("memory_pool")
        agent = controller_dict.get("agent{}".format(i + 1))

        data_action = {"device_id": "test_001", "task_id": 100, "fragment": "",
                       "type": 0, "xml": xml,
                       "activity": activity}
        result = agent.task_execution(data_action, controller_dict.get("memory_pool"))
        if result.response["status"] == 1:
            task_done = True
            break

        actionType = result.response["action_infos"][0]["action_type"]
        if actionType == android_controller.ActionType.NOP:
            pass
        elif actionType == android_controller.ActionType.CLICK:
            controller_dict.get("controller{}".format(i + 1)).tap(result.response["action_infos"][0]["bounds"][:2],
                                                                  result.response["action_infos"][0]["bounds"][2:])

        elif actionType == android_controller.ActionType.ACTIVATE:
            target_device = memory_pool.current_device
            if target_device > memory_pool.device_total_num:
                controller_dict[f"agent{target_device}"] = Operator_agent(target_device, 1)
                memory_pool.device_total_num += 1
                t = threading.Thread(target=task_execute, args=(target_device - 1, controller_dict))
                t.start()
        else:
            for item in result.response["action_infos"]:
                controller_dict.get("controller{}".format(i + 1)).execute_action(android_controller.ActionType.INPUT, item["bounds"], item["text"])
        sleep(2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", help="task's description")
    parser.add_argument("--dip", nargs='+', help="device's ip")
    args = parser.parse_args()
    task = args.task
    dtype = []
    dip = args.dip

    for i in range(len(dip)):
        dtype.append("default user")

    memory_pool = memory.MemoryPool()
    memory_pool.align_1(task, dtype, dip)
    sub_task_list = []
    for i in range(len(dip)):
        sub_task_list.append("")
    memory_pool.align_2(len(dip), sub_task_list, 1)
    controller_dict = {"memory_pool": memory_pool}
    agent1 = Operator_agent(1, 1)

    for i in range(len(dip)):
        controller_dict[f"d{i+1}"] = u2.connect(dip[i])
        controller_dict[f"controller{i+1}"] = android_controller.AndroidController(dip[i])
        controller_dict[f"agent{i + 1}"] = Operator_agent(i + 1, 1)

    while not task_done:
        current_device = memory_pool.current_device
        agent = controller_dict.get(f"agent{current_device}")
        device = controller_dict.get(f"d{current_device}")
        controller = controller_dict.get(f"controller{current_device}")
        sleep(1)
        xml = device.dump_hierarchy(compressed=False, pretty=False)
        activity = device.app_current().get("activity").split("/")[-1]
        data_action = {"xml": xml, "activity": activity}
        result = agent.task_execution(data_action, memory_pool)
        if result.response["status"] == 1:
            task_done = True
        else:
            actionType = result.response["action_infos"][0]["action_type"]
            if actionType == ActionType.NOP:
                pass
            elif actionType == ActionType.CLICK:
                controller_dict.get("controller{}".format(current_device)).tap(
                    result.response["action_infos"][0]["bounds"][:2],
                    result.response["action_infos"][0]["bounds"][2:])
            elif actionType == ActionType.BACK:
                controller_dict.get("controller{}".format(current_device)).back()
            else:
                for item in result.response["action_infos"]:
                    controller_dict.get("controller{}".format(current_device)).execute_action(android_controller.ActionType.INPUT,
                                                                                              item["bounds"],
                                                                                              item["text"])
