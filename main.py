from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig
from astrbot.api import logger
from datetime import date, timedelta ,datetime
import astrbot.api.message_components as Comp
class MyPlugin(Star):
    def __init__(self, context: Context, config:AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.isUseLlmRemind = self.config.get("isUseLlmToRemind",False)
        if self.isUseLlmRemind == True:
            self.llmProvider = self.config.get("llmProvider",False)
            self.llmPrompt = self.config.get("llmPrompt","")
        else:
            self.remindSentence = self.config.get("remindSentence","")
        self.isOpenUserLevel = self.config.get("isOpenUserLevel",True)
        self.startMoney = self.config.get("startMoney",1000)
        self.qdMoney=self.config.get("qdMoney",1000)
        self.makeLess=self.config.get("makeLess",500)
    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    
    @filter.command("qd",alias={"签到","每日签到","CheckIn"})
    async def qd(self, event: AstrMessageEvent):
        """这是一个签到指令"""
        userId=event.get_sender_id()
        isRegister = await self.get_kv_data(f"is{userId}Register",False)
        lastQdDate = await self.get_kv_data(f"{userId}LastQd",False)
        todayDate = date.today()
        if isRegister == True:#如果已注册
            if lastQdDate == todayDate:#如果上一次签到日期等于今天日期（即已签到）
                if self.isUseLlmRemind == True:#如果开启LLM提示语
                    useLlmToRemind= await self.context.llm_generate(
                        chat_provider_id = self.llmProvider,
                        prompt = self.llmPrompt,
                    )
                    yield event.plain_result(useLlmToRemind.completion_text)
                else:#发送固定提示语
                    yield event.plain_result(self.remindSentence)
            else:#签到逻辑
                userMoney:int = await self.get_kv_data(f"{userId}Money",0)
                userMoney += self.qdMoney
                await self.put_kv_data(f"{userId}Money",userMoney)
                await self.put_kv_data(f"{userId}LastQd",todayDate.isoformat())
                sendText = [
                    Comp.At(qq=userId),
                    Comp.Plain(f" 签到成功，余额+{self.qdMoney}")
                ]
                yield event.chain_result(sendText)
                
        else:#注册+签到
            remindRegister=[
                Comp.At(qq=userId),
                Comp.Plain(f" 用户未注册，已自动注册，初始账户余额为{self.startMoney}\n目前总金额为{self.startMoney+self.qdMoney}")
            ]
            await self.put_kv_data(f"is{userId}Register",True)
            await self.put_kv_data(f"{userId}Money",self.qdMoney+self.startMoney)
            await self.put_kv_data(f"{userId}LastQd",todayDate.isoformat())
            yield event.chain_result(remindRegister)
    @filter.command("rg",alias={"register"})
    async def register(self,event:AstrMessageEvent):
        userId=event.get_sender_id()
        isRegister = await self.get_kv_data(f"is{userId}Register",False)
        if isRegister == False:
            await self.put_kv_data(f"is{userId}Register",True)
            await self.put_kv_data(f"{userId}Money",self.startMoney)
            tellRegister=[
                Comp.At(qq=userId),
                Comp.Plain(f" 注册成功，初始账户余额{self.startMoney}")
            ]
            yield event.chain_result(tellRegister)
        else:
            userMoney = await self.get_kv_data(f"{userId}Money",0)
            userMoney -= self.makeLess
            await self.put_kv_data(f"{userId}Money",userMoney)
            yield event.plain_result(f"你已经注册过了，为了惩罚你浪费资源，现扣除你{self.makeLess}")
    
    @filter.command
    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
