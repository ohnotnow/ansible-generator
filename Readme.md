# Ansible Playbook Assistant

## Overview
This project aims to simplify the development of Ansible playbooks by providing functionalities such as auto-generation, validation, and testing of playbooks. It utilizes OpenAI's ChatCompletion API to generate and document playbooks and employs Docker for isolated test environments.

## Requirements
- Python 3.x
- Docker
- OpenAI API key

## Installation
Clone the repository and navigate into the project directory.
```bash
git clone https://github.com/ohnotnow/ansible-generator.git
cd ansible-generator
```

Install the required Python packages.
```bash
pip install -r requirements.txt
```

## Environment Variables
Make sure your OpenAI key is set as an environment variable
```env
export OPENAI_API_KEY=sk-....
```

## Usage
Run the assistant with a text prompt as an argument.
```bash
$ python main.py "Could you write me an ansible playbook that installs apache on ubuntu?"
🗣️ Talking to OpenAI
✅ Response received from OpenAI API
🔍 Linting Ansible script
💾 Saving code to WIP.yaml
🏃‍♀️ Running code in Docker
✅ Code executed successfully!
🗣️ Talking to OpenAI
✅ Response received from OpenAI API
🏃‍♀️ Running tests in Docker
🔍 Generating docs
🗣️ Talking to OpenAI
✅ Response received from OpenAI API
📺 Script:

---
title: 'Install Apache on Ubuntu'
description: 'Install and enable Apache2 service on Ubuntu'
---
- name: Install Apache on Ubuntu
  hosts: all
  become: true
  tasks:
    - name: Update apt package cache
      apt:
        update_cache: yes

    - name: Install Apache2
      apt:
        name: apache2
        state: present

    - name: Enable Apache2 service
      service:
        name: apache2
        state: started
        enabled: yes



💾 Saved to install_apache_on_ubuntu.yaml
```

## Features
- **Ansible Playbook Generation**: Create a new playbook based on the user prompt.
- **Linting**: Validate the generated playbook using `ansible-lint`.
- **Automated Testing**: Automatically generate and run InfraTest test cases.
- **Documentation**: Auto-generate front matter for Ansible scripts.

## License
This project is licensed under the MIT License - see the [License.md](License.md) file for details.
