import re
import argparse
from utils import coordinator_utils
from utils.base_utils import llm
from utils.base_utils import memory


class Coordinator_agent:
    def __init__(self, overview_task: str):
        self.llm = llm.GeneralGPT()
        self.messages = []
        self.overview_task = overview_task
        self.device_type_list = []
        self.device_num = 0
        self.sub_task_list = []
        self.first_device_num = 0

    def device_type_syn(self, device_type_list: list):
        self.device_type_list = device_type_list[:int(self.device_num)]

    # Get the number of devices.
    def get_device_num(self):
        prompt = coordinator_utils.prompt_coordinator_1 + coordinator_utils.prompt_coordinator_2(self.overview_task)
        coordinator_utils.add_new_mes(self.messages, prompt)
        result = self.llm.ask_gpt_message(messages=self.messages)
        self.messages.append(result)
        self.device_num = int(result['content'].split("'")[1])

    # Get the sub tasks for devices.
    def get_sub_task(self):
        prompt = coordinator_utils.prompt_coordinator_3(self.device_type_list)
        coordinator_utils.add_new_mes(self.messages, prompt)
        result = self.llm.ask_gpt_message(messages=self.messages)
        # print(result['content'])
        self.messages.append(result)
        match_text = result['content'].split('## Answer ##')[-1]
        all_tasks = [line[3:] for line in match_text.split('\n')[1:]]
        self.sub_task_list = all_tasks

    # Get the first device for task.
    def get_first_device(self):
        prompt = coordinator_utils.prompt_coordinator_4()
        coordinator_utils.add_new_mes(self.messages, prompt)
        result = self.llm.ask_gpt_message(messages=self.messages)
        self.messages.append(result)
        matches = re.findall(r"'(.*?)'", result['content'])
        self.first_device_num = int(re.search(r'\d+', matches[0]).group())

    def run_coordinator(self, device_type_list: list):
        self.get_device_num()
        self.device_type_syn(device_type_list)
        self.get_sub_task()
        self.get_first_device()

    #  Task creation phase, coordinator performs its execution.
    def task_create(self, device_type_list: list, device_ip_list: list, pool: memory.MemoryPool = None):
        if pool is None:
            pool = memory.MemoryPool()

        print("Coordinator is running...")

        pool.overview_task = self.overview_task
        self.run_coordinator(device_type_list)

        pool.align_1(self.overview_task, self.device_type_list, device_ip_list)
        pool.align_2(self.device_num, self.sub_task_list, self.first_device_num)

        print(f"\nTask: {self.overview_task}")
        print(f"Device total num: {self.device_num}")
        print(f"Device sub-task: ")
        for i in range(len(self.sub_task_list)):
            print(f"{i+1}:{self.sub_task_list[i]}")
        print(f"First sub-task: \n{self.sub_task_list[self.first_device_num-1]}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", help="task's description")
    # parser.add_argument("--dtype", nargs='+', help="device's (account) type")
    args = parser.parse_args()
    task = args.task
    # dtype = args.dtype
    dtype = []

    coordinator = Coordinator_agent(task)
    coordinator.get_device_num()
    for i in range(coordinator.device_num):
        dtype.append("default user")
    coordinator.task_create(dtype, [])
