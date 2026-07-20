#!/bin/bash
NAME='ITGeeker.net'
echo "This is \"${NAME}\" shell"

# 1. 提示用户输入新分支名称并创建切换
read -p "Please enter new branch name: " branch_name
git checkout -b "${branch_name}"

# 2. 提示用户输入提交日志
read -p "Please enter git update log: " commit_value

# 3. 暂存、提交、推送新分支并建立远程追踪关系
git add --all .
git commit -m "\"${commit_value}\" use quick push"
git push -u origin "${branch_name}"
