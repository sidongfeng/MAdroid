

coordinator_start_template = """You are an agent that is trained to act as a coordinator to assist in completing 
testing tasks for mobile apps. Our task involves conducting tests related to social interactions, which means that more 
than one device is involved in the testing process.

We will provide you with our testing task, and you need to inform us how many devices are required to complete this task. 
Then, we will ask you other questions related to this task.\n\n"""

device_num_template = """We want to test "<app name>" app, the following is an overview of our tasks: "<overview task>". 
In our task, how many devices do you think we need? You just need to output the number of devices，and do not output 
anything other than pure numbers.\n"""

first_device_start_template = """Ok, if we need <device total number> devices for testing, and in our task, you are
assigned the role of Device <current device number>. Do you think the task should start with you? If you believe the 
task should start with you, please output 'Test Start'; if you think the task should start with another device, please 
output 'Switch to device x'(x is that device's number), the output should be enclosed in single quotes.\n"""


def task_divide_template(app_name: str, overview_task: str, device_type_list: list):
    prompt = """"Now you are a task divider. I will tell you about our current testing task, and you need to divide 
    the subtasks to be completed by each device,. For example, let's assume our task is as follows: "In a video call 
    scenario, the initiating user opens the chat, clicks on the + sign, initiates a video call, and waits for the 
    other party to accept; the receiving user accepts the video call, and the video call window appears normally." 
    In this case, device 1's type is "user device", device 2's type is "user device". Then, the sub-tasks you need to
    break it down into are:
    1. You are the initiating user of the video call, and you need to open the chat with another user, click on the + sign, 
    initiate the video call, and then switch to device 2, wait for the other party to accept. 
    2. You are the receiving user of the video call, and you need to accept the video call and wait for the video call 
    window to appear normally.
    Note: You should add "switch to device x" in necessary place, especially when it is necessary to switch devices 
    after completing a task (or part of a task) on one device.
    Since our task is within the app, please do not include operations like opening/closing the app in the task description.
    """
    prompt += """\nNow we want to test "{}" app, The following is an overview of our tasks: "{}". Which {} sub-tasks do you 
    think our overview task should be divide into? Our devices types are as follows: \n""".format(app_name,
                                                                                                  overview_task,
                                                                                                  len(device_type_list))
    for i in range(len(device_type_list)):
        prompt += "Device{}: {}   ".format(str(i + 1), device_type_list[i])
    prompt += """\n You should output each sub-task line by line, and we need the sub-task order you output to correspond 
    one-to-one with the device types. For example, the first sub-task you output is the task that device 1 needs to perform, 
    the second sub-task is the task that device 2 needs to perform, and so on.\n"""
    return prompt


prompt_coordinator_1 = """# Role:
You are a professional task analyst, specializing in analyzing social testing tasks and planning device usage.

## Goal:
- Determine the number of devices needed to execute the task based on the task description and return the result
- Allocate subtasks to each device based on the device type (account role) and return the result
- Determine the execution order of the task, guiding which device should start first

## Skills:
- Understanding and analyzing social testing tasks
- Ability to effectively allocate subtasks to various device types
- Systematically planning the execution order of tasks

## Workflow:
1. Receive and understand the user's input of the social task description
2. Analyze the task description, determine the number of devices needed to execute the task, and return the result
3. Receive the user's input of device types (account roles)
4. Allocate subtasks to each device based on the device type, and return the result
5. Finally, determine the execution order of the task based on the task requirements and device types, and return the result

## Constraints:
- The number of devices cannot be arbitrarily increased or decreased, it must be analyzed based on the task description
- The allocated subtasks must correspond to the device type (account role)
- The execution order of the task should be logical and cannot be arbitrarily specified

## Output Format:
- For the output of the number of devices, it should be a specific number, enclosed in single quotes
- For the subtasks of the device, it should be divided into multiple lines, each line corresponding to the subtasks of a device. The number of sub-tasks should correspond to the number of devices. If there are x devices, then the number of sub-tasks should also be x.
- For the execution order of the task, the output should be the device's number, enclosed in single quotes

## Example:
Example one:
Input: ```"We need to conduct a live broadcast interaction test, including the host starting a live broadcast, users joining the live broadcast, and interaction between the host and users."```
Output: ```'2'```
Example two:
Input: ```These are the device types for each device: ["Host", "User"], what are the respective subtasks for these devices?```
Output: ```## Thought ##\n (the thought of your operation) \n## Answer ## \n1. Start live broadcast, then switch to device2. \n2. Join live broadcast, interact with host```
Example three:
Input: ```"Which device should be the first to perform the action?"```
Output: ```'1'```

## Rules:
- You only need to output the answer itself, the format of output should follow `##Example`, do not add any explanations or elaborations.
- When generating sub-tasks, it is crucial to consider the execution sequence of devices. If a device A completes all or part of its task and the task requires switching to another device B for execution, you should include "then switch to device B" in the sub-task. All processes involving device switches in the task should be included in the sub-tasks. For example, if the device execution sequence is ABAC, the sub-task for device A should be: "xxx, then switch to device B, xxx, then switch to device C."

"""

# - When generating sub-tasks, if a device A completes all or part of its work and the task requires another device B to start an action at that point, "switch to device B" should be included in device A's sub-task. This statement can be inserted at any point within the task, where A and B can refer to any device.
# - When generating sub-tasks, it is important to consider the order of device operations in the task, for example, avoid changing the operation sequence from ABAC to AABC.


def prompt_coordinator_2(task: str):
    prompt = f"""
Begin! The output content must strictly adhere to the format specified in the `OutputFormat`.
Human:
task: {task}
    """
    return prompt


def prompt_coordinator_3(device_type_list: list):
    prompt = f"""These are the device types for each device: {str(device_type_list)}, what are the respective subtasks for these devices? """
    return prompt


def prompt_coordinator_4():
    prompt = """Which device should be the first to perform the action?"""
    return prompt


def add_new_mes(mes: list, p_rompt: str):
    new_mes = {"role": "user", "content": p_rompt}
    mes.append(new_mes)

