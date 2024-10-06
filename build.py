import os
import sys
import subprocess
import platform

def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    if process.returncode != 0:
        print(f"Error: {error.decode('utf-8')}")
        sys.exit(1)
    return output.decode('utf-8')

def build_executable():
    # 确保 PyInstaller 已安装
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        run_command("pip install pyinstaller")

    # 主脚本名称
    main_script = "main.py"  # 替换为你的主脚本名称

    # 基本 PyInstaller 命令
    command = f"pyinstaller --onefile --windowed {main_script}"

    # 添加额外的数据文件（如果有）
    # command += " --add-data 'path/to/data:data'"

    # 根据操作系统添加特定选项
    if platform.system() == "Windows":
        command += " --icon=path/to/icon.ico"  # 替换为你的图标路径
    elif platform.system() == "Darwin":  # macOS
        command += " --icon=path/to/icon.icns"  # 替换为你的图标路径
    elif platform.system() == "Linux":
        command += " --icon=path/to/icon.png"  # 替换为你的图标路径

    # 运行 PyInstaller
    print("Building executable...")
    output = run_command(command)
    print(output)

    print(f"Build complete. Executable can be found in the 'dist' directory.")

if __name__ == "__main__":
    build_executable()