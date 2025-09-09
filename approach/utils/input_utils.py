import uuid
import re
import inflect
import numpy as np

from base_utils import llm


def xml_align(f: str):
    temp1 = """<hierarchy rotation="0">"""
    temp2 = """</hierarchy>"""

    if f.startswith("<?xml version="):
        return f[:f.index(">") + 1] + temp1 + f[f.index(">") + 1:] + temp2

    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" + temp1 + f + temp2


# Retrieve all components with unique identifiers.
def getAllComponents_uid(jsondata: dict):
    root = jsondata['hierarchy']

    queue = [(root, "")]
    res = []

    while queue:
        currentNode, father_id = queue.pop(0)
        currentNode['id'] = str(uuid.uuid4())  # Insert the unique ID into the "id" attribute of the node.
        currentNode['father_id'] = father_id
        if 'node' in currentNode:
            if type(currentNode['node']).__name__ == 'dict':
                queue.append((currentNode['node'], currentNode.get('id')))
                # res.append(currentNode['node'])
            else:
                for e in currentNode['node']:
                    queue.append((e, currentNode.get('id')))
                    # res.append(e)
        # else:
        res.append(currentNode)

    return res


# Select the parent component of the target component based on its ID.
def findParentComponent(components, target_component):
    if target_component['father_id'] == "":
        return target_component
    for component in components:
        if component['id'] == target_component['father_id']:
            return component
    return None


# Use a queue to retrieve all components below n levels of a component.
def getNLevelComponents(component, n):
    if n == 0:
        return []
    queue = [component]
    res = []
    level = 0
    while queue:
        level_size = len(queue)
        while level_size > 0:
            currentNode = queue.pop(0)
            level_size -= 1

            if 'node' in currentNode:
                if type(currentNode['node']).__name__ == 'dict':
                    queue.append(currentNode['node'])
                else:
                    for e in currentNode['node']:
                        queue.append(e)
            else:
                res.append(currentNode)
        level += 1
        if level >= n:
            break

    return res


def getNearbyComponent_nosysui(component):
    nearby_components = []
    for e in component:
        if 'node' not in e:
            if ('resource-id' in e and 'com.android.systemui' not in e['@resource-id']) and (
                'com.android.systemui' not in e['@package']):
                nearby_components.append(e)

    return nearby_components


def getComponent(component, components):
    for comp in components:
        is_same = True
        for key, value in component.items():
            if key in ['id', 'father_id']:
                continue
            if key not in comp or comp[key] != value:
                is_same = False
                break

        if is_same:
            return comp


def chooseFromXml(all_components: list, component,
                  num: int = 4):
    target_component = getComponent(component, all_components)
    parent_component = None
    for _ in range(num):
        parent_component = findParentComponent(all_components, target_component)
        target_component = parent_component
    nearby_components = getNLevelComponents(parent_component, 2 * num + 1)
    return nearby_components


# Retrieve all text input components on the screen.
def find_EditText(all_components: list):
    ans = []

    for e_component in all_components:
        # if e_component in ans:
        #     continue
        if "@base-class" in e_component and e_component["@base-class"] == "android.widget.EditText":
            ans.append(e_component)
        elif "@editable" in e_component and e_component["@editable"] == "true":
            ans.append(e_component)
        elif '@class' in e_component and (e_component['@class'] == 'android.widget.EditText' or
                                          e_component['@class'] == 'android.widget.AutoCompleteTextView' or
                                          e_component['@class'] == 'com.bytedance.ies.xelement.input.LynxInputView'):
            ans.append(e_component)
    return ans


# Retrieve the three possible attributes of a component that may contain text.
def get_basic_info(e_component: dict):
    key_list = ['id', 'text', 'text-hint', 'hint']
    key_at_list = ['resource-id', 'text', 'content-desc', 'hint']
    dict_info = {}

    for i in range(len(key_list)):
        dict_info[key_list[i]] = None
        for e_property in e_component:
            if key_at_list[i] in e_property.lower():
                dict_info[key_list[i]] = e_component[e_property]
                break
    return dict_info


# Description of the basic information of a component.
def component_basic_info(jsondata: dict):
    text_id = "The purpose of this component may be '<EditText id>'. "
    text_text = "The text on this component is '<text>'. "
    text_description = "The description of this component is '<text-hint>'. "
    text_hint = "The hint of this component is '<hint>'. "

    if jsondata['id'] == "" or jsondata['id'] is None:
        text_id = ""
    else:
        if '/' in jsondata['id']:
            EditText_id = jsondata['id'].split('/')[-1]
        else:
            EditText_id = jsondata['id']
        EditText_id = EditText_id.replace('_', ' ')
        text_id = text_id.replace('<EditText id>', EditText_id)

    if jsondata['text'] == "" or jsondata['text'] == None:
        text_text = ""
    else:
        text = jsondata['text']
        text_text = text_text.replace('<text>', text)

    if jsondata['text-hint'] == "" or jsondata['text-hint'] is None:
        text_description = ""
    else:
        description = jsondata['text-hint']
        text_description = text_description.replace('<text-hint>', description)

    if jsondata['hint'] == "" or jsondata['hint'] is None:
        text_hint = ""
    else:
        hint = jsondata['hint']
        text_hint = text_hint.replace('<hint>', hint)

    return text_id + text_text + text_description + text_hint + '\n'


# Generate the "content-desc" attribute for a component.
def use_context_info_generate_prompt(jsondata: dict):
    text_header = "Question: "
    text_app_name = "This is an mobile app. "
    text_activity_name = "On its <activity name> page, it has an input component. "
    text_text = "The text on this component is '<text>'. "
    text_id = "The purpose of this input component may be '<EditText id>'. "
    text_context_info = "Below is the relevant prompt information of the input component:\n<context information>"

    text_ask = ("What is the hint text of this input component? You just need to guess and output the answer, "
                "and the answer should be enclosed in double quotes. The output example is like: \"output content\"\n")

    if '.' in jsondata['activity_name']:
        activity_name = jsondata['activity_name'].split('.')[-1]
    else:
        activity_name = jsondata['activity_name']
    text_activity_name = text_activity_name.replace('<activity name>', activity_name)

    if jsondata['text'] == "" or jsondata['text'] == None:
        text_text = ""
    else:
        text = jsondata['text']
        text_text = text_text.replace('<text>', text)

    context_info = ""
    if len(jsondata['nearby_components']) > 0:
        for e in jsondata['nearby_components']:
            context_info += "There is a component adjacent to this input component. "
            context_info += component_basic_info(get_basic_info(e))

    if len(jsondata['nearby_components']) > 0:
        text_context_info = text_context_info.replace('<context information>', context_info)
    else:
        text_context_info = ""

    if jsondata['id'] == "" or jsondata['id'] is None:
        text_id = ""
    else:
        EditText_id = jsondata['id']
        text_id = text_id.replace('<EditText id>', EditText_id)

    question = text_header + text_app_name + text_activity_name + text_text + text_id + text_context_info + text_ask
    final_text = question

    return final_text


def parse_numeric_outputs(text):
    output = []
    step = 1
    for line in text.split('\n'):
        if re.match(f"{step}. ", line) is not None:
            m = re.findall(r'"(.*?)"', line)
            if len(m) > 0:
                output.append(m[0])
            else:
                output.append(line.split(f'{step}. ')[-1])
            step += 1
    return output


def parse_list_outputs(text):
    output = []
    for line in text.split('\n'):
        if line.startswith("- "):
            m = re.findall(r'"(.*?)"', line)
            if len(m) > 0:
                output.append(m[0])
            else:
                output.append(line.split('- ')[-1])

    return output


def parse_non_outputs(text):
    output = []
    for line in text.split('\n'):
        if line.strip() != "":
            m = re.findall(r'"(.*?)"', line)
            if len(m) > 0:
                output.append(m[-1])
    return output


class INPUT_UI:
    def __init__(self, activity_name: str, all_components: list, messages: list, is_fixed_text: int,
                 task: str, llm: llm.GeneralGPT):
        self.activity_name = activity_name
        self.all_components = all_components
        self.components_with_edit_text = find_EditText(all_components)
        self.messages = messages
        self.llm = llm
        self.prompt = self.init_prompt()
        self.is_fixed_text = is_fixed_text
        self.task = task

    def init_prompt(self):
        prompt = "Question: This is an mobile app. On its \"{}\" page, it has {} input component. ".format(
            self.activity_name,
            str(len(self.components_with_edit_text)))
        return prompt

    # Generate the text that should be filled into the component.
    def infer_inputs(self):
        if len(self.components_with_edit_text) == 0:
            return []

        p = inflect.engine()
        for i, e_component in enumerate(self.components_with_edit_text):
            if 'text' in e_component:
                self.prompt += '{} input component has a placeholder of "{}" with a content description of "{}". '.format(
                    p.ordinal(i + 1), e_component['@text'].replace('\n', ' '),
                    e_component['@content-desc'].replace('\n', ' '))
            else:
                self.prompt += '{} input component has no placeholder with a content description of {}. '.format(
                    p.ordinal(i + 1), e_component['@content-desc'].replace('\n', ' '))
            # If the Input component doesn't have text or the Text is empty, find nearby components' Text as a
            # replacement.
            if 'text' not in e_component or (
                'text' in e_component and e_component['@text'] == ''):
                nearby_components = chooseFromXml(self.all_components, e_component)
                if len(nearby_components) != 0:
                    self.prompt += '{} input component has a label of: '.format(p.ordinal(i + 1))
                    for t_component in nearby_components:
                        if 'text' in t_component and t_component['@text'] != '' and t_component['@text'] != e_component['@text']:
                            self.prompt += "\"{}\". ".format(t_component['@text'].replace('\n', ' '))
                            break
                    self.prompt += "."
        self.prompt += "\n"
        # Generate fixed text or random text.
        if self.is_fixed_text == 1:
            self.prompt += ("What text should I input in this or these components (provide specific examples)? We "
                            "have an extra task: \"{}\". For components that do not have specified fixed text input, "
                            "please provide specific examples. For the fixed text inputs mentioned in the task, "
                            "you need to select the specified component and output the fixed text mentioned in the "
                            "task. You just need to output the"
                            "answer for each component, do not contain any placeholder or content description. The "
                            "output should only include the results and be enclosed in double quotes. Each input "
                            "needs to provide 1 answer. You need to display the output line by line.").format(
                self.task)
        else:
            self.prompt += (
                'What text should I input in this or these components (provide specific examples)? You just need to '
                'output the answer for each component, do not contain any placeholder or content description. '
                'The output should only include the results and be enclosed in double quotes. Each input '
                'needs to provide 1 answer. You need to display the output line by line. ')
            # self.prompt += "The output should be in English"
        self.prompt += "\nAnswer:"

        new1_message = {"role": "user", "content": self.prompt}
        self.messages.append(new1_message)
        output = self.llm.ask_gpt_message(messages=self.messages)
        self.messages.append(output)

        parsed_numeric_output = parse_numeric_outputs(output['content'])
        parsed_list_output = parse_list_outputs(output['content'])
        parsed_non_output = parse_non_outputs(output['content'])
        parsed_output = [parsed_numeric_output, parsed_list_output, parsed_non_output][
            np.argmax([len(parsed_numeric_output), len(parsed_list_output), len(parsed_non_output)])]
        parsed_output = parsed_output[:len(self.components_with_edit_text)]
        print('\n---------------')
        for i in range(len(parsed_output)):
            print(f"Input text {i+1}: " + parsed_output[i])
        print('---------------\n')
        return parsed_output

