#!/usr/bin/env python
# coding: utf-8

import vk_api
import datetime
import config, sending, change, check
from database import *

@db_session
def get_codes(chat_id: int) -> list:
    return list(map(int, get(user.codes for user in User if user.chat_id == chat_id).split('\n')))


@db_session
def get_permission(chat_id: int) -> int:
    return get(user.permission for user in User if user.chat_id == chat_id)


@db_session
def get_keys() -> set:
    return set(select(text.key for text in Text))


vk_session = vk_api.VkApi(token=config.TOKEN)

from vk_api.longpoll import VkLongPoll, VkEventType

longpoll = VkLongPoll(vk_session)

vk = vk_session.get_api()

# Запуск прослушки
for event in longpoll.listen():

    # Если пришло новое сообщение сообществу:
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:

        # Добавление нового чата в бд
        if event.from_user:
            add_users({event.user_id})
        elif event.from_chat:
            add_users({event.chat_id})

        # Если ввели какую-то команду
        if check.permission(config.orginizers, event.user_id) and event.text[0] in {'/', '!', '.'}:

            # Разделение текста сообщения на команду и ее аргументы
            text = list(map(str, event.text.split()))
            command = text[0][1:]

            try:
                args = text[1:]
            except IndexError:
                args = []

            # Если команда существует, то отправить подтверждение начала выполнения команды
            if command in config.commands.keys():
                sending.message(
                    vk=vk,
                    ID=event.user_id if event.from_user else event.chat_id,
                    message=f'Вызвана команда {command} с аргументами {args} в '
                    f'{datetime.now().strftime("%H:%M")}'
                )

                # Обработчик команд
                # РАССЫЛКА key(название рассылки) permission(кому отправить)
                if check.permission(config.orginizers, event.user_id) and config.commands[command] == 1:

                    try:
                        key = args[0]
                    except:
                        key = 0

                    try:
                        permission = int(args[1])
                    except:
                        permission = -1

                    if key in get_keys() and permission != -1:
                        sending.default_sending(
                            vk=vk,
                            key=key,
                            permission=permission
                        )
                        sending.message(
                            vk=vk,
                            ID=event.user_id,
                            message=f'Рассылка отправлена'
                        )

                    else:
                        sending.message(
                            vk=vk,
                            ID=event.user_id,
                            message=f'Неверно введена команда'
                        )

                # ИЗМЕНИТЬ_ТЕКСТ key(название рассылки) permission(кому можно его отправлять) message(текст сообщения)
                elif check.permission(config.orginizers, event.user_id) and config.commands[command] == 2:
                    try:
                        key = args[0]
                    except:
                        key = 0

                    try:
                        permission = int(args[1])
                    except:
                        permission = -1

                    try:
                        message = ' '.join(args[2:])
                    except:
                        message = ''

                    if key and permission != -1 and message:

                        result = change.text(
                            admin=event.user_id,
                            key=key,
                            message=message,
                            permission=permission
                        )

                        sending.message(
                            vk=vk,
                            ID=event.user_id,
                            message=result
                        )

                    else:
                        sending.message(
                            vk=vk,
                            ID=event.user_id,
                            message=f'Неверно введена команда'
                        )

                # ДОБАВИТЬ_ТЕКСТ key(название рассылки) permission(кому можно его отправлять) message(текст сообщения)
                elif check.permission(config.orginizers, event.user_id) and config.commands[command] == 3:
                    try:
                        key = args[0]
                    except:
                        key = 0

                    try:
                        permission = int(args[1])
                    except:
                        permission = -1

                    try:
                        message = ' '.join(args[2:])
                    except:
                        message = ''

                    if key and permission != -1 and message:
                        add_texts({
                            key: [permission, message]
                        })

                        sending.message(
                            vk=vk,
                            ID=event.user_id,
                            message=f'Добавлен новый текст рассылки "{key}"'
                        )

                    else:
                        sending.message(
                            vk=vk,
                            ID=event.user_id,
                            message=f'Неверно введена команда'
                        )

                # НАЗНАЧИТЬ_КМ km_link(айди КМа) first_name(имя гостя) last_name(фамилия гостя)
                elif check.permission(config.orginizers, event.user_id) and config.commands[command] == 4:
                    try:
                        km_link = args[0]
                    except:
                        km_link = ''

                    try:
                        first_name = args[1]
                    except:
                        first_name = ''

                    try:
                        last_name = args[2]
                    except:
                        last_name = ''

                    if km_link and first_name and last_name:
                        result = change.KMLink(
                            km_limk=km_link,
                            first_name=first_name,
                            last_name=last_name
                        )

                        sending.message(
                            vk=vk,
                            ID=event.user_id,
                            message=result
                        )

                    else:
                        sending.message(
                            vk=vk,
                            ID=event.user_id,
                            message=f'Неверно введена команда'
                        )

                else:
                    sending.message(
                        vk=vk,
                        ID=event.user_id if event.from_user else event.chat_id,
                        message=f'Вызвана несуществующая команда {command} (или недостаточно прав) с аргументами'
                        f'{args} в {datetime.now().strftime("%H:%M")}'
                    )



        # Если ввели текстовое сообщение, то перевести дальше или направить к личному КМу
        else:
            codes = get_codes(event.user_id)
            try:
                code = int(event.text)
                if code in codes:
                    level = codes.index(code)
                    permission = get_permission(event.user_id)
                    if level + 1 == permission:
                        permission += 1
                        change.permission(
                            user_id=event.user_id,
                            permission=permission
                        )
                        sending.message(
                            vk=vk,
                            ID=event.user_id,
                            message=f'Поздравляю! Ты успешно прошёл {permission-1} этап'
                        )

                    else:
                        sending.message(
                            vk=vk,
                            ID=event.user_id,
                            message='Что-то неправильно. Если у тебя есть вопрос, пиши своему КМу: ' +
                                    sending.KMLink(event.user_id)
                        )

                else:
                    sending.message(
                        vk=vk,
                        ID=event.user_id,
                        message='Что-то неправильно. Если у тебя есть вопрос, пиши своему КМу: ' +
                                sending.KMLink(event.user_id)
                    )
            except:
                sending.message(
                    vk=vk,
                    ID=event.user_id,
                    message='Если у тебя есть вопрос, пиши своему КМу: ' +
                            sending.KMLink(event.user_id)
                )
