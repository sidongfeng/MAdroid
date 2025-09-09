ob_prompt1 = """
# Role: UI Test Observer

## Background:
- social test: Test tasks that require multiple devices to participate together, such as voice calls, live streaming with co-hosts, and so on.

## Goals:
- Your task is to determine, during the automated testing process of a social test task that involves multiple devices, whether the current task execution actions align with the correct testing path.

## Rules:
- The content we input includes the description of the current social test task, the identities of each device involved, and the device that requires evaluation at the moment.
- What you need to determine is whether there are any issues with the overall flow of the task. The operator may perform exploratory actions on the interface while operating the device (this is likely because the component to be operated is hidden deep within the interface). Such exploratory actions do not affect the correctness of the task flow. However, if a device consistently performs exploratory actions, then it indicates an incorrect flow.
- When evaluating the "Task done" instruction, you need to consider the action sequences of all devices. You only need to determine if all devices have completed their intended actions. If they have completed the relevant instructions, then it can be concluded that the task has been completed.

## ActionSpace:
Here are the actions that can occur in a social test:
- 'tap' + 'component'
    - description: This command is used to tap on a component. 'component' is the id of the component on the current interface. 
    - A simple use case can be 'tap' + 'component's id'， which taps the target component on the current page. 
- 'nop'
    - description: This command is used to do nothing.
    - A simple use case can be 'nop'. 
- 'Switch to device x' + 'message' 
    - description: This command is used to let another device operate. And 'message' is a summary of what you have done previously.
    - A simple use case can be 'Switch to device x' + 'message'. 
- 'Switch to input generation'
    - description: This command is used to input non-fixed text in current page.
    - A simple use case can be 'Switch to input generation'.
- 'Switch to input generation' + 'task'
    - description: This command is used to input fixed text in current page. When you feel the need to input fixed text, you should specify where to input and the input content to form a task returned together in 'task blank'.
    - A simple use case can be 'Switch to input generation' + 'search for "winter gloves" in the search box'.
- 'back'
    - description: This command is used to invoke the system's back operation (similar to using the back button).
    - A simple use case can be 'back'.
- 'Task done'
    - description: This command can be used when you believe that the current testing task has been completed. You should only use it after ensuring that you and all other devices have completed the relevant operations.
    - A simple use case can be 'Task done'

## Knowledge:
- For action 'Switch to device x' + 'message', this command is used to let another device operate. In our testing, at any given time, only one device can hold the execution token, and only the device holding the token is allowed to perform operations. The token is now on the device you assess. And when this device think its work is done, it will pass the token to another device. And 'message' is a summary of what this device had done. When the last action in the history information is 'switch to device...', it is crucial to focus on determining the correctness of this device switching action.

## OutputFormat:
### Thought ###
Your thought about the question.
### Answer ###
'yes/no' + '0/1/2/3/4...' + 'yes/no' + 'yes/no' + 'reason'

The content within the five single quotation marks is as follows:
1. 'yes/no': whether there is an issue
2. '0/1/2/3/4...': error location
3. 'yes/no': need to restart the task
4. 'yes/no': need for back() operation
5. 'reason': The reason why you think there are issues in task. If you think there is an issue in the task (first item is 'yes'), you should clearly specify the problem in the 'reason' field. If you believe there is no issue in the task, then the 'reason' field should be left empty (' ')
For example:
If you believe that the current screen content is incorrect and the issue was caused by the operation on screen 4, and you think there is no need to restart the task but only to go back to screen 4, your response to me should be: 'yes' + '4' + 'no' + 'yes' + 'xxx...'. If you believe there are no issues, your response to me should be: 'no' + '0' + 'no' + 'no' + ' '.

## Knowledge:
- "Restart task" means terminating the current task and starting over. This is a high-risk operation and should only be used if the current interface or task has reached an irrecoverable state. It is advised not to use this functionality lightly unless it is absolutely necessary.
- In some scenarios, special functionalities are hidden within buttons such as 'More', 'More Panel', or similar ones. When encountering operations that involve clicking on such components(more, more panel...), clicking on these components may not be an operational error, but rather an attempt to access hidden key features within these interfaces.
- The errors in the task can be classified into three levels. For the first level, which is considered a minor operational error within the current activity, the 'back' and 'restart' operations are not required. The output type for this level is 'yes' + '0/1/2...' + 'no' + 'no' + 'reason'. The second level of errors requires the 'back()' operation and is typically used when there is a significant deviation between the current interface and the expected result. The third level of errors occurs when the operation path enters a loop or when there are severe errors (e.g., multiple interfaces/operations not meeting the expected criteria), and in such cases, the 'restart()' operation is used.
- When you believe that the operator should click on another component on the current interface, you can simply set the judgment result as "incorrect path" without performing the "restart task" or "back" operations.
- We will also provide you with sub-tasks for the devices you need to evaluate. A sub-task is the task that the device needs to execute. In the sub-task, there will be a statement: "switch to device x," which indicates that after the device completes certain tasks (or part of it), it needs to perform the "switch to device x" action to switch to another device.
"""


def ob_prompt2(overview_task: str, device_type_list: list, current_device_num: int, device_sub_task_list: list):
    prompt = f"""
Begin! Please write your thoughts step-by-step in `### Thought ###` area and provide the result in `### Answer ###` area.
Human:
- task: {overview_task}
- device number: {len(device_type_list)}
- you are evaluate device {current_device_num} 
- sub-task of device {current_device_num} ("Sub-task" is the task that the device needs to execute.): {device_sub_task_list[current_device_num-1]}
- device type: """
    for i, item in enumerate(device_type_list):
        prompt += f"device {i+1}: {item}; "
    return prompt


def ob_prompt3(memory_list: list, device_num: int, current_screen_all_comps: str):
    prompt = f"""
Here is the historical information about our previous GUI screen and action. The sequence number of each action represents its execution order, with higher numbers indicating later execution.
"""
    for i, item in enumerate(memory_list):
        prompt += f"{i+1}. Device {item['device_id']}: Action: {item['action']}\n Action's Thought: {item['content']}\n\n"
    prompt += f"After these actions, Device {device_num} has reached a new screen. The components on the new screen is:\n{current_screen_all_comps}\n\n"
    prompt += "Your main criterion for judgment is the actions of each device, and the current interface can only be used as an auxiliary reference. If there is a conflict between the content on the current interface and the actions of the device, the judgment should prioritize the device's actions. This means that if the device actions are correct, the task can be considered executed correctly. Please assess whether there are any issues with the current task in the device you assess."
    return prompt


def ob_prompt_test(memory_list: list, device_num: int, current_screen_all_comps: str):
    prompt = f"""
    Here is the historical information about our previous GUI screen and action. The sequence number of each action represents its execution order, with higher numbers indicating later execution.
    """
    for item in memory_list:
        prompt += item
    prompt += f"After these actions, Device {device_num} has reached a new screen. The components on the new screen is:\n{current_screen_all_comps}\n\n"
    prompt += "Your main criterion for judgment is the actions of each device, and the current interface can only be used as an auxiliary reference. If there is a conflict between the content on the current interface and the actions of the device, the judgment should prioritize the device's actions. This means that if the device actions are correct, the task can be considered executed correctly. Please assess whether there are any issues with the current task in the device you assess."
    return prompt


observer_start_template_1 = """
You are an agent that is trained to complete judgment tasks on a smartphone. Our testing 
task involves social testing that requires multiple devices to participate. For example, two or more devices collaborating to 
complete tasks such as video calls, creating meetings, or live streaming with co-hosts. Please assess whether the 
current operational path is correct.

Here is some basic information of our inputs:

1. app's name
The app's name we are testing.

2. number of devices, identities, overview task
The task we are testing requires cooperation among multiple devices. We will tell you of the number of devices and 
their identity, with the overview task and the execution task(subtask) for the current device.(The sub-task includes 
only the tasks specific to the device you are currently operating.) 

3. execution token 
Our testing requires multiple devices to participate in executing tasks, with only one device 
performing operations at a time. The execution token is held by the device currently performing the task. When a 
device believes it has completed its task, it passes the token to another device. Your task is to determine if there 
are any issues with the task execution flow of the device holding the execution token.

4. previous action list and screen list
We will give you an action list of what we have done from first screen to previous screen. The action includes
'Tap + (component name)', 'Switch to device (x) + 'message'', 'Switch to Input Generation ..', 'back', and 'Task done'. The first one means to tap a
component, the second one means to passes the execution token to another device to perform its task, 'message' is what 
it had done, and the third one means to switch to another model to input appropriate content into the text input component.
'back' means that the device has used the back key operation. Generally, this operation is mentioned in the task prompt 
or when the device determines that the current screen has no further actionable steps and needs to return to the previous screen.
'Task done' means that device want to end the whole testing task. Furthermore, even after device switching, it is still 
possible to switch back to the current device from another device and continue executing unfinished task.
The format we provide you for the previous action list and screen list will be as follows: the first line will be 
'screen1: xxx', the second line will be 'action1: xxx', the third line will be 'screen2: xxx', and so on. This 
sequence represents the description of the first interface of the device as 'screen1'. Then, we performed 'action1' 
on 'screen1' and transitioned to 'screen2'. Subsequently, we performed actions on 'screen2'...

5. the latest screen
We will provide you with the latest screen after the latest action. To illustrate the current screen, we 
will provide you with all the components present in the current screen. It is important to note that the names of 
clickable components have been merged, including the sub-components of their respective regions.

In certain situations, such as during a call scenario, the content on the screen may automatically hide after a few 
seconds without any clicks. In such cases, it is possible that the first click is ineffective as it only reactivates 
the hidden interface. In this situation, it is possible clicking the component again that needs to be clicked. The content of 
the interface should be nearly identical in both instances, although the displayed time on the screen may differ.

In some scenarios, special functionalities are hidden within buttons such as 'More', 'More Panel', 
or similar ones. When encountering operations that involve clicking on such components(more, more panel...), it is advisable not to make 
an immediate judgment but to observe for one or two rounds of operations before assessing the correctness of these 
actions.

"""
# 一般的assess用template_2
observer_start_template_2 = """You need to assess if there are any issues with the current task execution. This 
includes, but is not limited to, determining if the current screen is the correct screen related to the task, 
if the operations on the screen are performed correctly, and if the switch of execution token or task termination is 
done correctly. Your response format to me should be "'yes/no (whether there is an issue)' + 'error location (current 
device)' + 'yes/no (need to restart the task)' + 'yes/no (need for back() operation)' + 'reason' (the reason why you 
think there are issues in task)". The back() operation is performed using the back button on the smartphone, 
that doesn't mean going back to the previous screen(like from screen 5 to screen 4), but using the built-in 'back' 
operation on the smartphone. If you think there is an issue in the task (first item is 'yes'), you should clearly 
specify the problem in the 'reason' field. If you believe there is no issue in the task, then the 'reason' field 
should be left empty (' ')

For example: The current task is 'Live streaming with audience interaction,' involving two devices. In terms of 
device types, device1 is the broadcaster and device2 is the audience. The current executing device is device1. The 
history of screens includes: screen 1 is 'xxx,' with the operation on that screen being 'tap' + 'xxx.' Screen 2... 
Screen 4 is 'xxx,' with the operation on that screen being 'xxx.' The current screen(current screen is screen 5) is 
'xxx.' In this scenario, if you believe that the current screen content is incorrect and the issue was caused by the 
operation on screen 4, and you think there is no need to restart the task but only to go back to screen 4, 
your response to me should be: 'yes' + '4' + 'no' + 'yes' + 'xxx...'. If you believe there are no issues, 
your response to me should be: 'no' + '0' + 'no' + 'no' + ' '.

To determine whether to use the back() operation for the last item in the response, you can make a judgment based on 
the activity. If you believe that the activity of the erroneous screen is different from the current screen's 
activity, then you can use the back() operation. If the activities of the two screens are the same, you should 
indicate the error location but do not need to use the back() operation. For example: 'yes' + '3' + 'no' + 'no' + 'xxx...'

Furthermore, the back() operation is considered a risky action as it may navigate the screen back to a previous 
interface before the initial screen. Therefore, the starting interface of a task should definitely not involve a 
back() operation. Additionally, you need to verify repeatedly if the current interface truly requires a backward 
navigation. If the issue can be resolved by reselecting a component ('yes' + 'x' + 'no' + 'no' + 'xxx...'), it is advisable to 
avoid using the back() operation.

Restarting the task is a riskier operation compared to the back() operation. It should only be used when you believe 
the task has reached a deadlock or when it is impossible to return to the initial screen.

"""

'''
And last, considering the amount of information you have, when you believe a task has no issues and all devices have 
completed their respective tasks, you need to output the 'Task done' command, appended at the end of the regular 
output. For example, if you believe task should be over, you should output: 'no' + '0' + 'no' + 'no' + 'Task done' + 'xxx...'. 
You need to consider all tasks of all devices globally, and only after they collectively complete the entire overview 
task can you choose to end the task. The completion of the task by a single device alone does not signify the 
completion of the entire task.
'''


def observer_prompt_start(app_name: str, overview_task: str, device_type_list: list,
                          current_device_num: int):
    prompt = ""
    prompt += """We are testing {} app, and the overview of the running task is {}. """.format(app_name, overview_task)
    prompt += """There are {} devices for the current task, and the types of these devices are: \n""".format(
        len(device_type_list))
    i = 1
    for type in device_type_list:
        prompt += """Device{}: {}, """.format(i, type)
        i += 1
    prompt += "\nThe device that hold the execution token is device {}, which is the device you should assess. \n".format(
        str(current_device_num))
    return prompt


def observer_prompt_history(device_num: int, history_screen_list: list, action_list: list, activity_name: str,
                            current_screen_all_comps: str):
    if len(history_screen_list) == 0:
        return ""
    prompt = (
        f"For device {str(device_num)} (which is the device you assess), it has a total of {len(history_screen_list)} historical operation screens. "
        f"Here are the descriptions of each screen and the actions performed on each screen.\n")
    print(f"history_screen_list: {len(history_screen_list)}")
    print(f"history_action_list: {len(history_screen_list)}")
    for i in range(len(history_screen_list)):
        prompt += f"screen {i + 1}: {history_screen_list[i]} \n"
        prompt += f"action {i + 1}: {action_list[i]} \n"
    prompt += (
        f"After these screens and actions, we reached a new screen. The screen's activity_name is '{activity_name}', "
        f"here are the components on the new screen:\n{current_screen_all_comps}\n")
    return prompt


def other_device_history(device_type_list: list, history_list: list, current_device: int, memory_list: list):
    prompt = (f"Below is the information of other device's screens and actions, these is some information to assist "
              f"you in making your judgment. You do not need to verify the content of the devices below.:\n")
    for i in range(len(device_type_list)):
        if i + 1 == current_device:
            continue
        prompt += f"Device{i + 1}({device_type_list[i]}): \n"
        for j in range(len(history_list[i].get("history_screen"))):
            prompt += f"screen {j + 1}: {history_list[i].get('history_screen')[j]}\n"
            if j < len(history_list[i].get("history_action")):
                prompt += f"action {j}: {history_list[i].get('history_action')[j]}\n"
    if len(memory_list) != 0:
        prompt += ("And below is the summary for the devices that performed their tasks before your assess "
                   "device. (The order is based on the execution order of the devices)\n")
        for item in memory_list:
            prompt += "Device {}(role: {}): \"message:{}\"".format(item['device_id'], item['role'], item['message'])
            prompt += "\n"
    return prompt


def observer_prompt_last():
    prompt = ("Please assess whether there are any issues with the current task in the device you assess. All you "
              "need to output is 'yes/no (whether there is an issue)' + 'error location (current device)' + 'yes/no "
              "(need to restart the task)' + 'yes/no (need for back() operation) + 'reason'(the reason why you think "
              "there are issues in task)'. You don't need to output any"
              "analysis, The four attributes in the output need to be enclosed in single quotation marks separately.")
    return prompt


device_switch_illustration = """
'Switch to device x' + 'message' 
This command is used to let another device operate. 
In our testing, at any given time, only one device can hold the execution token, and only the device holding the 
token is allowed to perform operations. The token is now on the device you assess. And when this device think its work 
is done, it will pass the token to another device. And 'message' is a summary of what this device had done.
"""


def observer_prompt_device_switch(app_name: str, overview_task: str, device_type_list: list, device_num: int,
                                  memory_list: list, matches: list, history_sub_messages: list, all_comps: str):
    prompt = observer_start_template_1
    prompt += observer_prompt_start(app_name, overview_task, device_type_list, device_num)
    prompt += f"Command description: {device_switch_illustration}"
    prompt += (f"Now, in our testing task, Device {str(device_num)} believes that it has completed its current stage "
               f"of the task and needs to pass the execution token to another device. Your task is to determine if "
               f"the current stage of the device's task is truly completed and if it has reached the point where a "
               f"device switch is required. (Some tasks may not require the device to complete all stages before "
               f"switching, for example, a task where Device A starts a live stream, Device B enters the live room, "
               f"and then Device A initiates a co-stream. In this case, the device switch can happen once Device A "
               f"starts the live stream.)\n")
    prompt += observer_prompt_history(device_num, history_sub_messages[device_num - 1]["history_screen"][:-1],
                                      history_sub_messages[device_num - 1]["history_action"],
                                      history_sub_messages[device_num - 1]["activity"][-1], all_comps)
    prompt += (f"Device {str(device_num)} want to pass the execution token to another device ({matches[0]}), and "
               f"what he had done is: {matches[1]}\n Your task is to determine whether the execution token should be "
               f"passed to that device. If you think it is time to pass the token, please output 'yes', or you can "
               f"output 'no' + 'reason'(why you think it is not the time to pass the token). The output should be "
               f"enclosed in single quotes,and the output should only include 'yes' or 'no' + 'reason'.\n")
    if len(memory_list) != 0:
        prompt += ("Below is the summary for the devices that performed their tasks before your assess "
                   "device. (The order is based on the execution order of the devices)\n")
        for item in memory_list:
            prompt += "Device {}(role: {}): \"message:{}\"".format(item['device_id'], item['role'], item['message'])
            prompt += "\n"
    prompt += f"For device {str(device_num)} (which is the device you assess), it has a summary of what it had done:\n"
    prompt += f"Device {str(device_num)} ({device_type_list[device_num - 1]}) summary: {matches[1]}\n"
    prompt += (
        f"You only need to determine whether the execution should be passed to another device({matches[0]}) by "
        f"outputting 'yes' or 'no' + 'reason'. No additional information needs to be provided, and 'yes' or 'no' + "
        f"'reason' should be enclosed in single quotation marks.")
    prompt += """

    """
    return prompt


def observer_prompt_task_done(app_name: str, overview_task: str, device_type_list: list, device_num: int,
                              memory_list: list, task_done_summary: str, history_sub_messages: list, all_comps: str):
    prompt = observer_start_template_1
    prompt += observer_prompt_start(app_name, overview_task, device_type_list, device_num)
    prompt += f"""
    Now, in our testing task, Device {str(device_num)} believes that its task, as well as the tasks of all other devices, have been 
    completed, and it wants to end the entire testing task. Your task is to determine whether the task is truly finished. 
    If you think the task is finished, please output 'yes', otherwise output 'no' + 'reason'(why you think it is not the time to pass the token).
    Here is the relevant information we provide regarding this task:\n"""
    prompt += observer_prompt_history(device_num, history_sub_messages[device_num - 1]["history_screen"][:-1],
                                      history_sub_messages[device_num - 1]["history_action"],
                                      history_sub_messages[device_num - 1]["activity"][-1],
                                      all_comps)
    if len(memory_list) != 0:
        prompt += ("Below is the summary for the devices that performed their tasks before your assess "
                   "device. (The order is based on the execution order of the devices)\n")
        for item in memory_list:
            prompt += "Device {}(role: {}): \"message:{}\"".format(item['device_id'], item['role'], item['message'])
            prompt += "\n"
    prompt += f"For device {str(device_num)} (which is the device you assess), it has a summary of what it had done:\n"
    prompt += f"Device {str(device_num)} ({device_type_list[device_num - 1]}) summary: {task_done_summary}\n"
    prompt += ("You only need to determine if the task has ended by outputting 'yes' or 'no' + 'reason'. No additional "
               "information needs to be provided, and 'yes' or 'no' + 'reason' should be enclosed in single quotation "
               "marks.")
    return prompt




