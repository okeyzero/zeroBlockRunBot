# zeroBlockRunBot

# 需要的module
web3，blocknative-sdk，requests


# zeroBlockRunBot

找到想要玩的项目的合约  观察哪个方法可能是项目方开启的（如 nft 哪个方法 是开启用户可以mint的）


编辑runBotconfig.json里的参数：

**RPC**：ETH节点RPC

**privateKey**：私钥数组["私钥1", "私钥2"]，有几个号加几个

**blocknativeKey**：https://www.blocknative.com/  创建个账号，个人中心获取，不需要设置，直接复制key即可

**barkKey**：IOS的bark软件推送key，用于推送mint成功或者失败信息（没有可以空着）

**maxValue**: 最大金额（设置0就只跟免费的，0.1就表示收费0.1以下的也跟）

**follow**：需要跟踪的项目方（owner 或合约）地址，"follow": {"owner地址":{"all": 是否所有方法都跟, [要跟随的方法]}

**to**：发起交易的to地址
**value**：发起交易的eth数量
**input**：发起交易的数据 如果数据包含地址 则用[address]代替
**gasLimit**：发起交易的gasLimit

# 报错

1，handshake failed

  网络连接不上blocknative，尝试更换服务器到外网服务器

# 已打包的exe
自行pyinstaller打包吧

直接提示错误的，应该是配置文件错误


# 打赏

0x5256F6475f0e0BFcf974064947E0eD8AEbd3BeF7

