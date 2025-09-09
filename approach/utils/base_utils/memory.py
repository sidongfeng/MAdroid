class MemoryPool:
    def __init__(self):
        self.current_device = 1
        self.is_info1_ok = False
        self.is_info2_ok = False

        self.overview_task = ""
        self.device_type_list = []
        self.device_ip_list = []

        self.device_total_num = 1
        self.device_sub_task_list = []

        self.memory_pool_list = []

    def align_1(self, overview_task: str, device_type_list: list, device_ip_list: list):
        self.overview_task = overview_task
        self.device_type_list = device_type_list
        self.device_ip_list = device_ip_list

        self.is_info1_ok = True

    def align_2(self, device_total_num: int, device_sub_task_list: list, first_device_id: int):
        self.device_total_num = device_total_num
        self.device_sub_task_list = device_sub_task_list
        self.current_device = first_device_id
        self.is_info2_ok = True

    # type0: action, type1: message(summary)
    def add_memory(self, content_type: str, device_id: str, action: str, content: str):
        new_mes = {'type': content_type, 'device_id': device_id, 'action': action, 'content': content}
        self.memory_pool_list.append(new_mes)

    def get_device_actions(self, device_id: str):
        action_list = []
        for item in self.memory_pool_list:
            if item['type'] == '0' and item['device_id'] == device_id:
                action_list.append(item)
        return action_list

    def get_all_messages(self):
        message_list = []
        for item in self.memory_pool_list:
            if item['type'] == '1':
                message_list.append({'device_id': item['device_id'], 'message': item['content']})
        return message_list

