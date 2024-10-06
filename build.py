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
    main_script = "main.py"

    # 可执行文件名称
    executable_name = "InvestmentTools"

    # 图标文件路径
    icon_path = os.path.join(os.getcwd(), "icon.png")

    # 在 build_executable 函数中添加这段代码
    # if platform.system() == "Windows":
    #     icon_path = os.path.join(os.getcwd(), "icon.ico")
    # elif platform.system() == "Darwin":  # macOS
    #     icon_path = os.path.join(os.getcwd(), "icon.icns")
    # else:  # Linux 和其他系统
    #     icon_path = os.path.join(os.getcwd(), "icon.png")

    # 检查图标文件是否存在
    if not os.path.exists(icon_path):
        print(f"Warning: Icon file {icon_path} not found. Proceeding without an icon.")
        icon_option = ""
    else:
        icon_option = f"--icon={icon_path}"

    # 基本 PyInstaller 命令
    command = f"pyinstaller --onefile --windowed --name={executable_name} {icon_option} {main_script}"

    # 添加额外的数据文件（如果有）
    # command += " --add-data 'path/to/data:data'"

    # 运行 PyInstaller
    print("Building executable...")
    output = run_command(command)
    print(output)

    print(f"Build complete. Executable '{executable_name}' can be found in the 'dist' directory.")


if __name__ == "__main__":
    build_executable()