import os
import json
import time
import asyncio
import platform
import requests
import threading
import websockets
from web3 import Web3
from datetime import datetime

# 这里是作为模板输出到config用，修改无用
configExample = {
    "RPC": "https://eth-goerli.alchemyapi.io/v2/CGG64AqKEBB1Dkru3JEt399-yfjwvfZd",  # RPC节点，得支持w3.eth.filter才行
    "privateKey": ["privateKey1", "privateKey2"],  # 私钥，支持多个
    "blocknativeKey": "",  # blocknative的key
    "alchemyKey": "",# alchemy的key，和blocknativeKey二选一即可
    "barkKey": "",
    "follow": {
        "0x5256F6475f0e0BFcf974064947E0eD8AEbd3BeF7": {"all": True, "MethodID":["0xa9059cbb"]}
    },# 监控指定人的操作 和指定的方法（任意方法  则 all 为 TRUE  监控到即刻开始抢跑
    "txInfo": {
        "to": "0x5256F6475f0e0BFcf974064947E0eD8AEbd3BeF7",
        "value": 0,
        "input": "0x",
        "gasLimit": 400000
    }#抢跑的数据  其中input中 [address] 会自动替换成私钥对应的address
}

# 输出颜色优化
if platform.system().lower() == 'windows':
    import ctypes
    import sys

    std_out_handle = ctypes.windll.kernel32.GetStdHandle(-11)


    def set_cmd_text_color(color, handle=std_out_handle):
        Bool = ctypes.windll.kernel32.SetConsoleTextAttribute(handle, color)
        return Bool


    def print_color(message, color):
        colorDict = {'green': 0x0a, 'red': 0x0c, 'blue': 0x0b, 'yellow': 0x0e}
        stime = time.strftime("%m-%d %H:%M:%S", time.localtime())
        set_cmd_text_color(colorDict[color])
        sys.stdout.write(f'[{stime}] {message}\n')
        set_cmd_text_color(0x0c | 0x0a | 0x09)
else:
    def print_color(message, color):
        colorDict = {'green': '32m', 'red': '31m', 'blue': '34m', 'yellow': '33m'}
        stime = time.strftime("%m-%d %H:%M:%S", time.localtime())
        print(f'[{stime}] \033[1;{colorDict[color]}{message}\033[0m')


# bark推送
def bark(info, data):
    if barkKey != '':
        requests.get('https://api.day.app/' + barkKey + '/' + info + '?url=' + data)


def canRun(_from,_methodID):
    if _from.lower() in follows:
        isAll = follows[_from.lower()]['all']
        if(isAll):
            return True
        methodIDList = follows[_from.lower()]['MethodID']
        for methodID in methodIDList:
            print(_methodID,methodID.lower())
            if(_methodID in methodID.lower()):
                return True
        else:return False
    return False


def minttx(_account, _privateKey,_gasPrice, _maxFeePerGas, _maxPriorityFeePerGas):
    inputData=txInput.replace("[address]",_account.address[2:].lower())
    try:
        transaction = {
            'from': _account.address,
            'chainId': chainId,
            'to': w3.toChecksumAddress(txToAddress),
            'gas': txGasLimit,
            'nonce': w3.eth.getTransactionCount(_account.address),
            'data': inputData,
            'value': txValue
        }
        if _gasPrice > 10000:
            transaction['gasPrice'] = _gasPrice
        else:
            transaction['maxFeePerGas'] = _maxFeePerGas
            transaction['maxPriorityFeePerGas'] = _maxPriorityFeePerGas

        signed = w3.eth.account.sign_transaction(transaction, _privateKey)
        new_raw = signed.rawTransaction.hex()
        tx_hash = w3.eth.sendRawTransaction(new_raw)
        print_color("抢跑交易发送成功" + w3.toHex(tx_hash), 'green')
        freceipt = w3.eth.waitForTransactionReceipt(tx_hash, 600)
        if freceipt.status == 1:
            print_color("抢跑成功   " + w3.toHex(tx_hash), 'green')
            bark('抢跑成功', 'https://cn.etherscan.com/tx/' + w3.toHex(tx_hash))
        else:
            print_color("抢跑失败", 'red')
            bark('抢跑失败', 'https://cn.etherscan.com/tx/' + w3.toHex(tx_hash))
    except Exception as e:
        print_color('交易失败:' + str(e), 'red')
        return


def txn_handler(to_address, from_address, inputData, value, gasPrice, maxFeePerGas, maxPriorityFeePerGas, hash):
    to_address = w3.toChecksumAddress(to_address)
    MethodID = inputData[:10]
    print_color(from_address + "监控到新交易", 'yellow')
    print_color("交易hash :" + hash, 'yellow')
    gasInfo = f"gasPrice :{gasPrice}" if gasPrice > 10000 else f"maxFeePerGas :{maxFeePerGas}\nmaxPriorityFeePerGas :{maxPriorityFeePerGas}"
    print_color(f"交易内容如下:\nfrom :{from_address}\nto :{to_address}\nvalue :{value}\ninput :{inputData}\n{gasInfo}",
                'yellow')
    if not (canRun(from_address, MethodID)):
        print_color('似乎是无关的交易:' + hash, 'red')
        return
    for index in range(len(accounts)):
        threading.Thread(target=minttx, args=(accounts[index], privateKeys[index], gasPrice,  maxFeePerGas, maxPriorityFeePerGas)).start()


def network_id_to_name(network_id: int) -> str:
    return {
        1: 'main',
        3: 'ropsten',
        4: 'rinkeby',
        5: 'goerli',
        42: 'kovan',
        100: 'xdai',
        56: 'bsc-main',
        137: 'matic-main',
        250: 'fantom-main'
    }[network_id]


async def blocknative():
    async for websocket in websockets.connect('wss://api.blocknative.com/v0'):
        try:
            initialize = {
                "categoryCode": "initialize", "eventCode": "checkDappId",
                "dappId": blocknativeKey, "timeStamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                "version": "1",
                "blockchain": {"system": "ethereum", "network": networkId}
            }
            await websocket.send(json.dumps(initialize))
            for _follow in follows:
                configs = {
                    "categoryCode": "configs", "eventCode": "put",
                    "config": {"scope": _follow, "filters": [{"from": _follow, "status": "pending"}], "watchAddress": True},
                    "dappId": blocknativeKey,
                    "timeStamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
                    "version": "1",
                    "blockchain": {"system": "ethereum", "network": networkId}
                }
                await websocket.send(json.dumps(configs))
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30*60)
                except asyncio.TimeoutError:
                    print_color('30分钟无消息，可能断开，尝试重连', 'red')
                    await websocket.close()
                    break
                json_data = json.loads(message)
                if json_data['status'] == 'ok' and 'event' in json_data:
                    if json_data['event']['categoryCode'] == 'initialize':
                        print_color('初始化成功', 'blue')
                    elif json_data['event']['categoryCode'] == 'configs':
                        print_color(f"监控{json_data['event']['config']['scope']}地址成功", 'blue')
                    elif json_data['event']['categoryCode'] == 'activeAddress':
                        txn = json_data['event']['transaction']
                        to_address, from_address, inputData, hash , value= txn['to'], txn['from'], txn['input'], txn['hash'], int(txn['value'])
                        if 'maxFeePerGas' in txn:
                            tx_gasPrice = 0
                            tx_maxFeePerGas, tx_maxPriorityFeePerGas = int(txn['maxFeePerGas']), int(txn['maxPriorityFeePerGas'])
                        else:
                            tx_gasPrice = int(txn['gasPrice'])
                            tx_maxFeePerGas, tx_maxPriorityFeePerGas = 0, 0
                        threading.Thread(target=txn_handler, args=(to_address, from_address, inputData,value,tx_gasPrice ,tx_maxFeePerGas, tx_maxPriorityFeePerGas, hash)).start()
                    else:
                        print_color(message, 'blue')
        except Exception as e:
            print_color(str(e), 'red')
            await websocket.close()


async def alchemy():
    async for websocket in websockets.connect(f'wss://eth-goerli.g.alchemy.com/v2/{alchemyKey}'):
        try:
            json_data = {
                "jsonrpc": "2.0",
                "id": 1, "method": "eth_subscribe", "params": []
            }
            for _follow in follows:
                json_data['params'] = ["alchemy_filteredNewFullPendingTransactions", {"address": _follow}]
                await websocket.send(json.dumps(json_data))
                result = await websocket.recv()
                if "result" in result:
                    print_color(f"监控{_follow}地址成功", 'blue')
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30*60)
                except asyncio.TimeoutError:
                    print_color('30分钟无消息，可能断开，尝试重连', 'red')
                    await websocket.close()
                    break
                json_data = json.loads(message)
                if 'params' in json_data:
                    txn = json_data['params']['result']
                    to_address, from_address, inputData, hash, value = txn['to'], txn['from'], txn['input'], txn['hash'], int(txn['value'], 16)
                    if from_address.lower() not in follows:
                        return
                    if 'maxFeePerGas' in txn:
                        tx_gasPrice = 0
                        tx_maxFeePerGas, tx_maxPriorityFeePerGas = int(txn['maxFeePerGas'], 16), int(txn['maxPriorityFeePerGas'], 16)
                    else:
                        tx_gasPrice = int(txn['gasPrice'], 16)
                        tx_maxFeePerGas, tx_maxPriorityFeePerGas = 0, 0
                    threading.Thread(target=txn_handler, args=(to_address, from_address, inputData, value, tx_gasPrice, tx_maxFeePerGas, tx_maxPriorityFeePerGas, hash)).start()
        except Exception as e:
            print_color(str(e), 'red')
            await websocket.close()


if __name__ == '__main__':
    print_color("用于0区块抢跑", 'red')
    print_color("有能力的请使用源码，不对使用者安全负责", 'red')
    print_color("打狗请用小号，无法保证无bug", 'red')
    print_color("开源地址：https://github.com/okeyzero/zeroBlockRunBot", 'red')
    print_color("代码水平较差，有任何优化建议请反馈", 'red')
    if not os.path.exists('runBotconfig.json'):
        print_color('请先配置runBotconfig.json', 'blue')
        file = open('runBotconfig.json', 'w')
        file.write(json.dumps(configExample))
        file.close()
        time.sleep(10)
    try:
        file = open('runBotconfig.json', 'r')
        config = json.loads(file.read())
        RPC, privateKeys = config['RPC'], config['privateKey']
        blocknativeKey, alchemyKey,barkKey, follows = config['blocknativeKey'], config['alchemyKey'], config['barkKey'], config['follow']
        follows = dict((k.lower(), v) for k, v in follows.items())
        w3 = Web3(Web3.HTTPProvider(RPC))
        chainId = w3.eth.chainId
        networkId=network_id_to_name(chainId)
        txInfo = config['txInfo']
        txToAddress = txInfo['to']
        txValue = txInfo['value']
        txValue = w3.toWei(txValue, 'ether')
        txInput = txInfo['input']
        txGasLimit = txInfo['gasLimit']
        print_color('chainId ' + str(chainId), 'red')
        print_color('监控链(main代表eth链) :' + networkId, 'red')
        accounts = [w3.eth.account.privateKeyToAccount(privateKey) for privateKey in privateKeys]
        if len(alchemyKey) >= 20:
            asyncio.run(alchemy())
        elif len(blocknativeKey) >= 20:
            asyncio.run(blocknative())
        else:
            print_color('blocknativeKey和alchemyKey必须提供一个', 'red')
    except Exception as e:
        print_color(str(e), 'red')
        time.sleep(10)
