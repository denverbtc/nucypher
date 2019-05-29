import pytest
from nucypher.blockchain.eth.interfaces import BlockchainInterface
from nucypher.blockchain.eth.clients import (
    GethClient, ParityClient, GanacheClient, EthTestClient)


class MockGethProvider:

    clientVersion = 'Geth/v1.4.11-stable-fed692f6/darwin/go1.7'


class MockParityProvider:

    clientVersion = 'Parity-Ethereum/v2.5.1-beta-e0141f8-20190510/x86_64-linux-gnu/rustc1.34.1'


class MockGanacheProvider:
    clientVersion = 'EthereumJS TestRPC/v2.1.5/ethereum-js'


class ChainIdReporter:
    chainId = 5


class MockWeb3():

    net = ChainIdReporter

    def __init__(self, provider):
        self.provider = provider

    @property
    def clientVersion(self):
        return self.provider.clientVersion



class BlockChainInterfaceTestBase(BlockchainInterface):

    Web3 = MockWeb3

    def _configure_registry(self, *args, **kwargs):
        pass

    def _setup_solidity(self, *args, **kwargs):
        pass


class GethClientTestInterface(BlockChainInterfaceTestBase):

    def _get_IPC_provider(self):
        return MockGethProvider()


class ParityClientTestInterface(BlockChainInterfaceTestBase):

    def _get_IPC_provider(self):
        return MockParityProvider()


class GanacheClientTestInterface(BlockChainInterfaceTestBase):

    def _get_HTTP_provider(self):
        return MockGanacheProvider()


def test_geth_web3_client():
    interface = GethClientTestInterface(
        provider_uri='file:///ipc.geth'
    )
    assert isinstance(interface.client, GethClient)
    assert interface.backend == 'darwin'
    assert interface.node_version == 'v1.4.11-stable-fed692f6'
    assert interface.is_local is False
    assert interface.chainId == 5


def test_parity_web3_client():
    interface = ParityClientTestInterface(
        provider_uri='file:///ipc.parity'
    )
    assert isinstance(interface.client, ParityClient)
    assert interface.backend == 'x86_64-linux-gnu'
    assert interface.node_version == 'v2.5.1-beta-e0141f8-20190510'


def test_ganache_web3_client():
    interface = GanacheClientTestInterface(
        provider_uri='http:///ganache:8445'
    )
    assert isinstance(interface.client, GanacheClient)
    assert interface.node_version == 'v2.1.5'
    assert interface.is_local