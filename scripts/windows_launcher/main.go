// Windows 启动器：双击后调用内置 python 打开组卷界面。
package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
)

func main() {
	exe, err := os.Executable()
	if err != nil {
		pause("无法定位程序路径: " + err.Error())
		os.Exit(1)
	}
	root := filepath.Dir(exe)
	if err := os.Chdir(root); err != nil {
		pause("无法进入程序目录: " + err.Error())
		os.Exit(1)
	}

	python := filepath.Join(root, "python", "python.exe")
	app := filepath.Join(root, "app.py")
	if _, err := os.Stat(python); err != nil {
		pause("未找到内置 Python:\n" + python)
		os.Exit(1)
	}
	if _, err := os.Stat(app); err != nil {
		pause("未找到 app.py:\n" + app)
		os.Exit(1)
	}

	cmd := exec.Command(python, app)
	cmd.Dir = root
	cmd.Env = append(os.Environ(),
		"PYTHONUTF8=1",
		"PYTHONIOENCODING=utf-8",
		"PYTHONPATH="+root,
		"PATH="+filepath.Join(root, "python")+string(os.PathListSeparator)+os.Getenv("PATH"),
	)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin

	fmt.Println("正在启动组卷界面…")
	fmt.Println("若浏览器未自动打开，请访问 http://127.0.0.1:8765/")
	if err := cmd.Run(); err != nil {
		pause("启动失败: " + err.Error())
		os.Exit(1)
	}
}

func pause(msg string) {
	fmt.Println(msg)
	fmt.Println("按回车键退出…")
	fmt.Scanln()
}
