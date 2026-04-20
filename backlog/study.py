from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import os
import json


def open_website_with_anti_detection():
    try:
        # 1. 基础配置 - 浏览器选项
        chrome_options = Options()

        # 指定用户数据目录，保留浏览器指纹和登录状态
        user_data_dir = r"D:\python_project\anti_bot\UserData"
        if not os.path.exists(user_data_dir):
            os.makedirs(user_data_dir)
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

        # 2. 反检测核心配置 - 隐藏WebDriver特征
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # 隐藏自动化标识
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])  # 排除自动化开关
        chrome_options.add_experimental_option('useAutomationExtension', False)  # 禁用自动化扩展

        # 3. 模拟真实浏览器环境
        # 设置高版本User-Agent，接近真实用户
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        chrome_options.add_argument(f"user-agent={user_agent}")

        # 指定Chrome浏览器二进制文件路径
        chrome_binary_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        if os.path.exists(chrome_binary_path):
            chrome_options.binary_location = chrome_binary_path

        # 4. 浏览器环境优化
        chrome_options.add_argument("--disable-gpu")  # 禁用GPU加速，避免被部分反爬系统检测
        chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")  # 禁用站点隔离
        # 随机窗口尺寸，模拟真实用户的不同设备
        chrome_options.add_argument(f"--window-size={random.randint(1366, 1920)},{random.randint(768, 1080)}")

        # 5. 驱动配置
        chrome_driver_path = r"D:\chromedriver\chromedriver.exe"
        service = Service(chrome_driver_path)

        # 6. 创建浏览器驱动
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # 7. 注入JavaScript隐藏WebDriver特征，这是反检测的关键步骤
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                // 隐藏WebDriver标识
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
                // 模拟真实的Chrome浏览器属性
                window.navigator.chrome = {
                    runtime: {},
                    browser: {
                        getVersion: () => '115.0.5790.170'
                    }
                }
                // 模拟媒体设备，避免因缺少摄像头/麦克风权限被检测
                navigator.mediaDevices = {
                    getDevices: () => Promise.resolve([])
                }
                // 模拟浏览器加载完成事件
                window.dispatchEvent(new Event('load'))
            """
        })

        # 8. 打开目标网站，这里以指纹检测页面为例
        driver.get("https://fingerprintjs.github.io/BotD/main/")
        print("已打开指纹检测页面，请查看检测结果")

        # 9. 模拟人机行为 - 滚动和延时
        wait = WebDriverWait(driver, 10)
        for _ in range(3):
            scroll_height = driver.execute_script("return document.body.scrollHeight")
            # 随机滚动到页面不同位置
            driver.execute_script(f"window.scrollTo(0, {random.randint(0, scroll_height)})")
            # 随机延时，模拟人类操作节奏
            time.sleep(random.uniform(1, 3))

        # 10. 打印页面检测结果
        try:
            result_element = wait.until(EC.presence_of_element_located((By.ID, 'result')))
            print("页面检测结果:", result_element.text)
        except:
            print("未获取到检测结果元素")

        # 保持窗口打开，手动查看检测结果
        input("按Enter键关闭浏览器...")

    except Exception as e:
        print(f"出现错误: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()
            print("浏览器已关闭")


if __name__ == "__main__":
    open_website_with_anti_detection()


    4	成都市中级人民法院	法官助理（四）	10100004	8	本科及以上	学士及以上	"本科：法学类
研究生：法学类"	A类《法律职业资格证书》	限女性	本科为普通高等学校毕业并获得相应学位，符合本职位学历、学位、专业要求	028-82915794

