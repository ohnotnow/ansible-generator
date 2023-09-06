import openai
import docker
import os
import argparse
import subprocess
import yaml
import json
from enum import Enum

# Define model and token prices
class Model(Enum):
    GPT4_32k = ('gpt-4-32k', 0.03, 0.06)
    GPT4 = ('gpt-4', 0.06, 0.12)
    GPT3_5_Turbo_16k = ('gpt-3.5-turbo-16k', 0.003, 0.004)
    GPT3_5_Turbo = ('gpt-3.5-turbo', 0.0015, 0.002)

openai.api_key = os.getenv("OPENAI_API_KEY")
openai_model = os.getenv("OPENAI_MODEL", Model.GPT3_5_Turbo.value[0])
token_count = 0

def get_token_price(token_count, model_engine=openai_model):
    token_price_input = 0
    token_price_output = 0
    for model in Model:
        if model_engine.startswith(model.value[0]):
            token_price_output = model.value[2] / 1000
            break
    return round(token_price_output * token_count, 4)

def lint_ansible_script(ansible_script):
    print('🔍 Linting Ansible script')
    try:
        yaml.safe_load(ansible_script)
    except yaml.YAMLError as exc:
        print("👀 An error occurred while parsing the yaml:")
        print(exc)
        return False

    # Write the script to a temporary file
    with open('temp.yaml', 'w') as f:
        f.write(ansible_script)

    try:
        # Run ansible-lint and capture the standard output and standard error
        result = subprocess.run(["ansible-lint", "--profile=min", "temp.yaml"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Ansible-Lint failed with exit code {result.returncode}.")
            print(result.stdout)
            print(result.stderr)
            return False

    except subprocess.CalledProcessError as e:
        print(f"Ansible-Lint failed with exit code {e.returncode}.")
        return False

    return True

def get_openai_response(messages=[], functions=None):
    print('🗣️ Talking to OpenAI')
    global token_count
    openai_args = {}
    openai_args['messages'] = messages
    openai_args['model'] = openai_model
    if functions:
        function_name = functions[0]['name']
        openai_args['functions'] = functions
        openai_args['function_call'] = {"name": function_name}

    response = openai.ChatCompletion.create(**openai_args)

    print("✅ Response received from OpenAI API")
    message = response['choices'][0]['message']
    tokens_used = response['usage']['total_tokens']
    token_count += tokens_used
    if message.get("function_call"):
        function_name = message["function_call"]["name"]
        function_args = json.loads(message["function_call"]["arguments"])
        title = function_args.get("title")
        description=function_args.get("description")
        return title, description
    else:
        reply = message['content'].strip()
        messages.append({"role": "assistant", "content": reply})
        return reply, messages

def get_ansible_description(ansible_script):
    print('🔍 Generating docs')
    # Write the script to a temporary file
    with open('temp.yaml', 'w') as f:
        f.write(ansible_script)

    conversation = [
        {
            "role": "system",
            "content": "You are a terse assistant specialized in helpful front-matter for ansible scripts. You must ALWAYS respond with just the front-matter - no explanations, no comments, no markdown formatting."
        },
        {
            "role": "user",
            "content": f"Generate docs for this Ansible script:\n\n{ansible_script}"
        }
    ]
    functions = [
        {
            "name": "get_ansible_title_and_description",
            "description": "Gets a suitable title and short description for an Ansible script",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "A suitable title for the Ansible script",
                    },
                    "description": {
                        "type": "string",
                        "description": "A short description of the Ansible script",
                    }
                },
                "required": ["title", "unit"],
            },
        }
    ]

    try:
        title, description = get_openai_response(conversation, functions=functions)
        return {"title": title, "description": description}
    except Exception as e:
        print("👀 An error occurred while generating docs:")
        print(e)
        return None, None

def get_infratest_script(ansible_script):
    print('📝 Generating Infratest script')
    conversation = [
        {
            "role": "system",
            "content": "You are a terse assistant specialized in writing python InfraTest tests using pytest-testinfra for ansible scripts. You must ALWAYS respond with just the python code - no explanations, no comments, no markdown formatting."
        },
        {
            "role": "user",
            "content": f"Please give me pytest-testinfra code for the following  Ansible script::\n\n{ansible_script}"
        }
    ]

    code, messages = get_openai_response(conversation)
    code = code.replace("```python", "")
    code = code.replace("```", "")
    code = code.replace('r"""', '')
    code = code.replace('"""', '')
    code = code.replace("r'''", '')
    code = code.replace("'''", '')

    return code

def get_ansible_script(prompt, messages=None):
    # set the initial system prompt
    conversation = [
        {"role": "system", "content": "You are a terse assistant specialized in generating Ansible scripts. You must ALWAYS respond with just code - no explanations, no comments, no markdown formatting."}
    ]

    if messages:
        conversation.extend(messages)

    conversation.append({"role": "user", "content": prompt})

    code, messages = get_openai_response(conversation)

    code = code.replace("```python", "")
    code = code.replace("```", "")


    try:
        is_valid = lint_ansible_script(code)
        if not is_valid:
            print("👀 An error occurred while linting the code:")
            print(lint_results)
            return None, messages
    except Exception as e:
        print("👀 An error occurred while linting the code:")
        print(e)
        return None, messages

    # Add this round of conversation to messages for potential future iterations
    messages.append({"role": "assistant", "content": code})

    return code, messages

def save_code_to_file(code):
    print('💾 Saving code to WIP.yaml')
    with open("WIP.yaml", "w") as f:
        f.write(f"{code}\n")

def run_code_in_docker():
    client = docker.from_env()
    current_dir = os.path.abspath(os.getcwd())  # Get the absolute path of the current directory

    try:
        print('🏃‍♀️ Running code in Docker')
        # Pull Python image
        # client.images.pull("python:3.9")

        # Run multiple commands inside the container
        # cmd = "pip install -r /app/requirements.txt && python /app/WIP.py"
        cmd = ['sh', '-c', 'pip install --root-user-action=ignore ansible && ansible-playbook /app/WIP.yaml']

        # Create and run the container
        container = client.containers.create(
            "python:3.9",
            command=cmd,
            volumes={current_dir: {'bind': '/app', 'mode': 'rw'}},  # Bind the current directory to /app in the container
        )

        container.start()

        try:
            exit_code = container.wait()['StatusCode']
        except Exception as e:
            print(f"\n\n👀 A docker error occurred: {e}\n\n")
            exit_code = 1

        # Fetch the stdout and stderr
        stdout_bytes = container.logs(stdout=True, stderr=False)
        stderr_bytes = container.logs(stdout=False, stderr=True)

        # Decode to string
        stdout = stdout_bytes.decode('utf-8')
        stderr = stderr_bytes.decode('utf-8')

        # Remove the container
        container.remove()

        return stdout, stderr, exit_code

    except Exception as e:
        print(f"\n\n👀 An error occurred: {e}\n\n")
        return None, str(e), 1

def run_tests_in_docker(code, tests):
    playbook = yaml.safe_load(code)

    # Modify the 'hosts' field for each play in the playbook so we don't hit any naming errors
    for play in playbook:
        play['hosts'] = 'localhost'

    # Convert the modified playbook back to a YAML string
    code = yaml.safe_dump(playbook)

    with open("WIP.yaml", "w") as f:
        f.write(f"{code}\n")
    with open("test_ansible.py", "w") as f:
        f.write(f"{tests}\n")
    with open("inventory.yaml", "w") as f:
        f.write(f"all:\n  hosts:\n    localhost:\n      ansible_connection: local\n")

    client = docker.from_env()
    current_dir = os.path.abspath(os.getcwd())  # Get the absolute path of the current directory

    try:
        print('🏃‍♀️ Running tests in Docker')
        # Pull Python image
        # client.images.pull("python:3.9")

        # Run multiple commands inside the container
        # cmd = "pip install -r /app/requirements.txt && python /app/WIP.py"
        cmd = ['sh', '-c', 'pip install --root-user-action=ignore --upgrade pip; pip install --root-user-action=ignore ansible pytest pytest-testinfra && ansible-playbook --connection=local -i /app/inventory.yaml /app/WIP.yaml && pytest']

        # Create and run the container
        container = client.containers.create(
            "python:3.9",
            command=cmd,
            working_dir="/app",
            volumes={current_dir: {'bind': '/app', 'mode': 'rw'}},  # Bind the current directory to /app in the container
        )

        container.start()

        try:
            exit_code = container.wait()['StatusCode']
        except Exception as e:
            print(f"\n\n👀 A docker error occurred: {e}\n\n")
            exit_code = 1

        # Fetch the stdout and stderr
        stdout_bytes = container.logs(stdout=True, stderr=False)
        stderr_bytes = container.logs(stdout=False, stderr=True)

        # Decode to string
        stdout = stdout_bytes.decode('utf-8')
        stderr = stderr_bytes.decode('utf-8')

        # Remove the container
        container.remove()

        return stdout, stderr, exit_code

    except Exception as e:
        print(f"\n\n👀 An error occurred: {e}\n\n")
        return None, str(e), 1

def main():
    max_retries = 5
    retries = 0
    messages = []

    parser = argparse.ArgumentParser(description='Process some text.')
    parser.add_argument('prompt', type=str, help='The prompt to send to OpenAI')

    args = parser.parse_args()
    prompt = args.prompt

    while retries < max_retries:
        code, messages = get_ansible_script(prompt, messages)
        if not code:
            retries += 1
            continue

        save_code_to_file(code)

        output, errors, exit_code = run_code_in_docker()

        if int(exit_code) > 0:
            # Send errors and previous messages back to API for refinement
            messages.append({"role": "user", "content": f"Execution failed: {errors}"})
            retries += 1
            print(f"❌ Execution failed: {errors}\n")
            continue

        print("✅ Code executed successfully!")
        tests = get_infratest_script(code)
        output, errors, exit_code = run_tests_in_docker(code, tests)
        if int(exit_code) > 0:
            # Send errors and previous messages back to API for refinement
            messages.append({"role": "user", "content": f"Execution failed: {errors} {output}"})
            retries += 1
            print(f"❌ Execution failed: {errors}\n\n{output}\n")
            print("(Ignoring for demo)")
            # break
        front_matter = get_ansible_description(code)
        original_string = front_matter['title']
        lower_string = original_string.lower()
        underscore_string = lower_string.replace(" ", "_")
        filename = underscore_string + ".yaml"
        finished_script = f"---\ntitle: '{front_matter['title']}'\ndescription: '{front_matter['description']}'\n{code}\n\n"
        print(f"📺 Script:\n\n{finished_script}\n\n")
        with open(filename, "w") as f:
            f.write(finished_script)
        print(f"💾 Saved to {filename}")
        print(f"💰 Token price: US${get_token_price(token_count)} for {token_count} tokens\n\n")
        break

if __name__ == "__main__":
    main()
