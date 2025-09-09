import argparse
import threading
from time import sleep

import uiautomator2 as u2
import xmltodict

from utils import operator_utils
from utils.base_utils.android_controller import ActionType
from utils.base_utils import memory
from utils.base_utils import android_controller
import Coordinator
import Operator
import Observer

task_done = False


def get_all_comps(xml: str):
    if "<hierarchy rotation=" in xml:
        align_xml = xml
    else:
        align_xml = operator_utils.xml_align(xml)
    xml_dict = xmltodict.parse(align_xml)
    all_comps = operator_utils.getMergedComponents(xml_dict)
    t_list = []
    operator_utils.component_prompt("", all_comps, t_list)
    return t_list[0]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", help="task's description")
    # parser.add_argument("--dtype", nargs='+', help="device's account type")
    parser.add_argument("--dip", nargs='+', help="device's ip")
    args = parser.parse_args()

    task = args.task
    # dtype = args.dtype
    dtype = []
    dip = args.dip

    if not dtype:
        for i in range(len(dip)):
            dtype.append("default user")

    memory_pool = memory.MemoryPool()
    controller_dict = {"memory_pool": memory_pool}

    coordinator = Coordinator.Coordinator_agent(task)
    observer = Observer.Observer_agent()

    coordinator.task_create(dtype, dip, memory_pool)
    device_type_list = coordinator.device_type_list

    observer.align1(task, device_type_list, coordinator.sub_task_list)

    for i in range(len(device_type_list)):
        controller_dict[f"d{i + 1}"] = u2.connect(dip[i])
        controller_dict[f"controller{i + 1}"] = android_controller.AndroidController(dip[i])
        controller_dict[f"agent{i + 1}"] = Operator.Operator_agent(i + 1, 1)

    all_comps = ""
    while not task_done:
        current_device = memory_pool.current_device
        agent = controller_dict.get(f"agent{current_device}")
        device = controller_dict.get(f"d{current_device}")
        controller = controller_dict.get(f"controller{current_device}")
        sleep(1)
        xml = device.dump_hierarchy(compressed=False, pretty=False)
        # sleep(2)
        activity = device.app_current().get("activity").split("/")[-1]
        all_comps = get_all_comps(xml)

        o_result = observer.run_observer(0, current_device, all_comps, memory_pool)
        if "action_infos" in o_result.response and "react" in o_result.response["action_infos"][0]:
            react = o_result.response["action_infos"][0]["react"]
            observer_reason = o_result.response["observer_response"]
            agent.observer_judge_flag = True
            agent.observer_reason = observer_reason

            if react == 2:
                controller.back()
                print("Observer: back")
                observer.observer_skip_flag = True
                continue
            if react == 3:
                task_done = True
                break
            if react == 1:
                print()

        data_action = {"xml": xml, "activity": activity}
        result = agent.task_execution(data_action, memory_pool)

        if result.response["status"] == 1:
            pass
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
        if "device_switch" in result.response:
            o_result = observer.run_observer(1, current_device, all_comps, memory_pool)
            if "action_infos" in o_result.response and "react" in o_result.response["action_infos"][0] and o_result.response["action_infos"][0]["react"] != 0:
                agent.observer_reason = o_result.response["observer_response"]
                memory_pool.current_device = current_device
                agent.device_switch_flag = True
                observer.observer_skip_flag = True
        if "task_done" in result.response:
            o_result = observer.run_observer(2, current_device, all_comps, memory_pool)
            if "action_infos" in o_result.response and "react" in o_result.response["action_infos"][0] and o_result.response["action_infos"][0]["react"] != 0:
                agent.observer_reason = o_result.response["observer_response"]
                agent.task_not_done_flag = True
                observer.observer_skip_flag = True
            else:
                task_done = True

