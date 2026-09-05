import os
import asyncio
import logging
from typing import List
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.models import NetworkState, ActionType, RouterVendor, TrafficJob
from core.state_manager import NetworkFSM
from worker.executor import TrafficExecutor

# Carrega variáveis do arquivo .env
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TrafficBot")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USERS: List[int] = [
    int(uid.strip()) for uid in os.getenv("ALLOWED_TELEGRAM_IDS", "0").split(",") if uid.strip().isdigit()
]


class MockRedisLock:
    """Lock assíncrono para controle de concorrência."""
    _locks = {}

    def __init__(self, router_id: str):
        self.router_id = router_id

    async def acquire(self) -> bool:
        if self._locks.get(self.router_id, False):
            return False
        self._locks[self.router_id] = True
        return True

    async def release(self):
        self._locks[self.router_id] = False


class TelegramTrafficBot:
    def __init__(self, executor: TrafficExecutor, lock_manager_factory):
        self.bot = Bot(token=BOT_TOKEN)
        self.dp = Dispatcher()
        self.executor = executor
        self.lock_manager_factory = lock_manager_factory
        self._register_handlers()

    def _build_status_text(self, info_note: str = "") -> str:
        state_icons = {
            NetworkState.NORMAL_DEFAULT: "🟢 NORMAL_DEFAULT (Tráfego Padrão)",
            NetworkState.SHUNTED_OP1: "🟡 SHUNTED_OP1 (Forçado na Operadora 1)",
            NetworkState.SHUNTED_OP2: "🟡 SHUNTED_OP2 (Forçado na Operadora 2)",
            NetworkState.FAILED_DIRTY: "🔴 FAILED_DIRTY (Requer Atenção)",
        }
        icon_desc = state_icons.get(self.executor.current_state, self.executor.current_state.value)
        text = (
            f"📡 <b>Painel de Engenharia de Tráfego ISP</b>\n\n"
            f"• <b>Estado da Rede:</b> <code>{icon_desc}</code>\n"
            f"• <b>Roteador Borda:</b> <code>MikroTik RouterOS (172.28.100.5)</code>\n"
            f"• <b>Upstreams:</b> Operadora 1 (AS 65001) | Operadora 2 (AS 65002)\n"
            f"• <b>Prefixo:</b> <code>200.100.0.0/22</code>\n"
        )
        if info_note:
            text += f"\n💡 <i>{info_note}</i>\n"
        text += "\nSelecione uma ação permitida abaixo:"
        return text

    def _build_status_keyboard(self) -> types.InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        state = self.executor.current_state

        if state == NetworkState.NORMAL_DEFAULT:
            builder.button(text="➡️ Desviar p/ Operadora 1", callback_data="action:SHUNT_TO_OP1")
            builder.button(text="➡️ Desviar p/ Operadora 2", callback_data="action:SHUNT_TO_OP2")
        elif state in (NetworkState.SHUNTED_OP1, NetworkState.SHUNTED_OP2):
            builder.button(text="🔄 Retornar ao Padrão (Rollback)", callback_data="action:ROLLBACK_DEFAULT")
        elif state == NetworkState.FAILED_DIRTY:
            builder.button(text="⚠️ Forçar Reconciliação", callback_data="action:RECONCILE")

        builder.button(text="🔄 Atualizar Status", callback_data="action:REFRESH")
        builder.adjust(1)
        return builder.as_markup()

    def _register_handlers(self):
        @self.dp.message(Command("start", "status", "help"))
        async def cmd_status(message: types.Message):
            # Validação de segurança básica (Whitelist)
            if ALLOWED_USERS != [0] and message.from_user.id not in ALLOWED_USERS:
                await message.reply(
                    f"⛔ <b>Acesso não autorizado.</b>\nSeu Telegram ID é: <code>{message.from_user.id}</code>.\nAdicione-o no <code>.env</code> em <code>ALLOWED_TELEGRAM_IDS</code> para liberar o acesso.",
                    parse_mode="HTML"
                )
                return

            text = self._build_status_text()
            await message.answer(text, reply_markup=self._build_status_keyboard(), parse_mode="HTML")

        @self.dp.callback_query(F.data.startswith("action:"))
        async def handle_action(callback: types.CallbackQuery):
            # Validação de segurança em cliques de botão (Whitelist)
            if ALLOWED_USERS != [0] and callback.from_user.id not in ALLOWED_USERS:
                await callback.answer(
                    f"⛔ Não autorizado! Seu ID ({callback.from_user.id}) não está na lista.",
                    show_alert=True
                )
                return

            action_str = callback.data.split(":")[1]

            if action_str == "REFRESH":
                try:
                    await callback.message.edit_text(
                        self._build_status_text(info_note="Status atualizado em tempo real."),
                        reply_markup=self._build_status_keyboard(),
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.debug(f"Refresh ignorado (conteúdo idêntico): {e}")
                await callback.answer("Status atualizado.")
                return

            if action_str == "RECONCILE":
                self.executor.current_state = NetworkState.NORMAL_DEFAULT
                await callback.message.edit_text(
                    self._build_status_text(info_note="Reconciliação forçada concluída."),
                    reply_markup=self._build_status_keyboard(),
                    parse_mode="HTML"
                )
                await callback.answer()
                return

            action = ActionType(action_str)
            user_id = callback.from_user.id

            job = TrafficJob(
                job_id=f"JOB-{int(asyncio.get_event_loop().time())}",
                action=action,
                vendor=RouterVendor.MIKROTIK,
                target_router_ip="172.28.100.5",
                username="admin",
                password="admin",
                requested_by_user_id=user_id,
                requested_by_username=callback.from_user.username,
            )

            # Fast-Ack no Telegram
            await callback.answer("⏳ Solicitação aceita! Iniciando orquestração...")
            status_msg = await callback.message.answer(f"🚀 <b>Job [{job.job_id}] Iniciado...</b>", parse_mode="HTML")

            async def update_telegram(msg_text: str):
                try:
                    await status_msg.edit_text(f"🚀 <b>Job [{job.job_id}]</b>\n{msg_text}", parse_mode="HTML")
                except Exception as e:
                    logger.debug(f"Erro ao atualizar status temporário: {e}")

            lock_manager = self.lock_manager_factory(job.target_router_ip)

            asyncio.create_task(
                self._run_and_notify(job, lock_manager, update_telegram, callback.message)
            )

    async def _run_and_notify(self, job, lock_manager, status_cb, original_msg):
        success = await self.executor.execute_job(job, lock_manager, status_callback=status_cb)
        try:
            status_desc = f"Última ação: {job.action.value} ({'Sucesso' if success else 'Falhou'})"
            new_text = self._build_status_text(info_note=status_desc)
            await original_msg.edit_text(new_text, reply_markup=self._build_status_keyboard(), parse_mode="HTML")
        except Exception as e:
            logger.error(f"Erro ao atualizar mensagem original do painel: {e}")

    async def start_polling(self):
        logger.info("🤖 Bot do Telegram iniciado! Aguardando comandos via Polling...")
        await self.dp.start_polling(self.bot)


async def main():
    executor = TrafficExecutor(current_network_state=NetworkState.NORMAL_DEFAULT)
    lock_factory = lambda rid: MockRedisLock(rid)
    bot_app = TelegramTrafficBot(executor, lock_factory)
    await bot_app.start_polling()


if __name__ == "__main__":
    asyncio.run(main())

