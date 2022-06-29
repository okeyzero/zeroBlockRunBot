import os
import json
import time
import platform
import threading
import requests
from blocknative.stream import Stream
from web3 import Web3

# 这里是作为模板输出到config用，修改无用
configExample = {
    "RPC": "https://mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161",  # RPC节点
    "privateKey": ["privateKey1", "privateKey2"],  # 私钥，支持多个
    "blocknativeKey": "",  # blocknative的key
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

async def txn_handler(txn, unsubscribe):
    to_address = txn['to']
    from_address = txn['from']
    to_address = w3.toChecksumAddress(to_address)
    hash=txn['hash']
    inputData = txn['input']
    MethodID = inputData[:10]

    value = int(txn['value'])
    gasPrice = 0
    maxFeePerGas = 0
    maxPriorityFeePerGas = 0
    if 'gasPrice' in txn:
        gasPrice = int(txn['gasPrice'])
    else:
        maxFeePerGas = int(txn['maxFeePerGas'])
        maxPriorityFeePerGas = int(txn['maxPriorityFeePerGas'])
    print_color(from_address + "监控到新交易", 'yellow')
    gasInfo= f"gasPrice :{gasPrice}" if gasPrice>10000 else f"maxFeePerGas :{maxFeePerGas}\nmaxPriorityFeePerGas :{maxPriorityFeePerGas}"
    print_color(f"交易内容如下:\nfrom :{from_address}\nto :{to_address}\nvalue :{value}\ninput :{inputData}\n{gasInfo}", 'yellow')
    if not (canRun(from_address,MethodID)):
        print_color('似乎是无关的交易:' + hash, 'red')
        return
    for index in range(len(accounts)):
        threading.Thread(target=minttx, args=(accounts[index], privateKeys[index], gasPrice, maxFeePerGas, maxPriorityFeePerGas)).start()
def main():
    while True:
        try:
            stream = Stream(blocknativeKey,network_id=chainId)
            print_color('初始化成功', 'blue')
            print_color('开始监控', 'blue')
            for _follow in follows:
                filters = [{
                    "status": "pending",
                    "from": _follow
                }]
                stream.subscribe_address(_follow, txn_handler, filters)
                print_color(f"监控{_follow}地址成功", 'blue')
            stream.connect()
        except Exception as e:
            print_color(str(e), 'red')
            time.sleep(10)

if __name__ == '__main__':
    print_color("用于0区块抢跑", 'red')
    print_color("无法保证无bug", 'red')
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
        blocknativeKey, barkKey, follows = config['blocknativeKey'], config['barkKey'], config['follow']
        follows = dict((k.lower(), v) for k, v in follows.items())
        w3 = Web3(Web3.HTTPProvider(RPC))
        chainId = w3.eth.chainId
        txInfo = config['txInfo']
        txToAddress = txInfo['to']
        txValue = txInfo['value']
        txValue =w3.toWei(txValue, 'ether')
        txInput = txInfo['input']
        txGasLimit = txInfo['gasLimit']
        print_color('chainId '+str(chainId), 'red')
        accounts = [w3.eth.account.privateKeyToAccount(privateKey) for privateKey in privateKeys]
        main()
    except Exception as e:
        print_color(str(e), 'red')
        time.sleep(10)
