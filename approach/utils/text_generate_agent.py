import xmltodict

from base_utils import llm
from base_utils import android_controller
import input_utils


class ReturnData:
    def __init__(self, data_type: int, device_switch: int, response: dict):
        # data_type: 0 normal return during the task_execute phase 1 device switching
        # 2 normal return during the task_create phase
        self.data_type = data_type
        self.device_switch = device_switch
        self.response = response


class Text_generate_agent:
    def __init__(self, additional_info: str):
        self.llm = llm.GeneralGPT()
        # extra task for input generation
        self.additional_info = additional_info

    # Generate the content to be filled into the text_input component by LLM.
    def input_generate(self, execute_info: dict, fixed_or_not: int, task: str):
        messages = [{"role": "system", "content": "You are a helpful input generator."}]
        xml = execute_info.get("xml")
        if "<hierarchy rotation=\"0\">" in xml:
            align_xml = xml
        else:
            align_xml = input_utils.xml_align(xml)
        activity = execute_info.get("activity")
        xml_dict = xmltodict.parse(align_xml)
        all_components = input_utils.getAllComponents_uid(xml_dict)
        components_with_edit_text = input_utils.find_EditText(all_components)

        if len(components_with_edit_text) == 0:
            temp_res = {"action_infos": [], "status": 0}
            mes = {"action_type": android_controller.ActionType.NOP}
            temp_res["action_infos"].append(mes)
            return ReturnData(0, 0, temp_res)

        no_hint_text = []
        for e in components_with_edit_text:
            if e['@content-desc'] == '':
                no_hint_text.append(e)

        for e_component in no_hint_text:
            component_info = input_utils.get_basic_info(e_component)
            nearby_components = input_utils.chooseFromXml(all_components, e_component)
            component_info['nearby_components'] = nearby_components
            component_info['activity_name'] = activity

            prompt = input_utils.use_context_info_generate_prompt(component_info)
            new_message = {"role": "user", "content": prompt}
            messages.append(new_message)
            result = self.llm.ask_gpt_message(messages=messages)
            real_content_desc = result['content']
            for e in all_components:
                if e['id'] == e_component['id']:
                    e['@content-desc'] = real_content_desc

        iu = input_utils.INPUT_UI(activity, all_components, messages, fixed_or_not, task, self.llm)
        result = iu.infer_inputs()
        for i in range(len(result)):
            result[i] = result[i].replace(" ", "\ ")
        response = {"action_infos": [], "status": 0}
        for i in range(len(result)):
            mes = {"action_type": android_controller.ActionType.INPUT,
                   "bounds": [int(num) for substring in components_with_edit_text[i]['@bounds'].strip("[]").split("][")
                              for num in substring.split(",")],
                   "resource_id": components_with_edit_text[i]['@resource-id'],
                   "class": components_with_edit_text[i]['@class'],
                   "text": result[i],
                   "throttle": 500}
            response["action_infos"].append(mes)
        return ReturnData(0, 0, response)
