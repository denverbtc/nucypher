"""
This file is part of nucypher.

nucypher is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

nucypher is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with nucypher.  If not, see <https://www.gnu.org/licenses/>.
"""
import datetime

import maya
import pytest
from eth_account._utils.signing import to_standard_signature_bytes

from nucypher.characters.lawful import Enrico
from nucypher.characters.unlawful import Vladimir
from nucypher.crypto.api import verify_eip_191
from nucypher.crypto.powers import SigningPower
from nucypher.utilities.sandbox.constants import INSECURE_DEVELOPMENT_PASSWORD
from nucypher.utilities.sandbox.middleware import MockRestMiddleware
from nucypher.utilities.sandbox.ursula import make_federated_ursulas, make_decentralized_ursulas


def test_new_federated_ursula_announces_herself(ursula_federated_test_config):
    ursula_in_a_house, ursula_with_a_mouse = make_federated_ursulas(ursula_config=ursula_federated_test_config,
                                                                    quantity=2,
                                                                    know_each_other=False,
                                                                    network_middleware=MockRestMiddleware())

    # Neither Ursula knows about the other.
    assert ursula_in_a_house.known_nodes == ursula_with_a_mouse.known_nodes

    ursula_in_a_house.remember_node(ursula_with_a_mouse)

    # OK, now, ursula_in_a_house knows about ursula_with_a_mouse, but not vice-versa.
    assert ursula_with_a_mouse in ursula_in_a_house.known_nodes
    assert ursula_in_a_house not in ursula_with_a_mouse.known_nodes

    # But as ursula_in_a_house learns, she'll announce herself to ursula_with_a_mouse.
    ursula_in_a_house.learn_from_teacher_node()

    assert ursula_with_a_mouse in ursula_in_a_house.known_nodes
    assert ursula_in_a_house in ursula_with_a_mouse.known_nodes


def test_stakers_bond_to_ursulas(testerchain, test_registry, stakers, ursula_decentralized_test_config):

    ursulas = make_decentralized_ursulas(ursula_config=ursula_decentralized_test_config,
                                         stakers_addresses=testerchain.stakers_accounts,
                                         workers_addresses=testerchain.ursulas_accounts,
                                         confirm_activity=False)

    assert len(ursulas) == len(stakers)
    for ursula in ursulas:
        ursula.validate_worker(registry=test_registry)
        assert ursula.verified_worker


def test_blockchain_ursula_substantiates_stamp(blockchain_ursulas):
    first_ursula = list(blockchain_ursulas)[0]
    signature_as_bytes = first_ursula.decentralized_identity_evidence
    signature_as_bytes = to_standard_signature_bytes(signature_as_bytes)
    assert verify_eip_191(address=first_ursula.worker_address,
                          message=bytes(first_ursula.stamp),
                          signature=signature_as_bytes)

    # This method is a shortcut for the above.
    assert first_ursula._stamp_has_valid_signature_by_worker()


def test_blockchain_ursula_verifies_stamp(blockchain_ursulas):
    first_ursula = list(blockchain_ursulas)[0]

    # This Ursula does not yet have a verified stamp
    first_ursula.verified_stamp = False
    first_ursula.validate_worker()

    # ...but now it's verified.
    assert first_ursula.verified_stamp


@pytest.mark.skip("See Issue #1075")    # TODO: Issue #1075
def test_vladimir_cannot_verify_interface_with_ursulas_signing_key(blockchain_ursulas):
    his_target = list(blockchain_ursulas)[4]

    # Vladimir has his own ether address; he hopes to publish it along with Ursula's details
    # so that Alice (or whomever) pays him instead of Ursula, even though Ursula is providing the service.

    # He finds a target and verifies that its interface is valid.
    assert his_target.validate_interface()

    # Now Vladimir imitates Ursula - copying her public keys and interface info, but inserting his ether address.
    vladimir = Vladimir.from_target_ursula(his_target, claim_signing_key=True)

    # Vladimir can substantiate the stamp using his own ether address...
    vladimir.substantiate_stamp(client_password=INSECURE_DEVELOPMENT_PASSWORD)
    vladimir.validate_worker = lambda: True
    vladimir.validate_worker()  # lol

    # Now, even though his public signing key matches Ursulas...
    assert vladimir.stamp == his_target.stamp

    # ...he is unable to pretend that his interface is valid
    # because the interface validity check contains the canonical public address as part of its message.
    with pytest.raises(vladimir.InvalidNode):
        vladimir.validate_interface()

    # Consequently, the metadata as a whole is also invalid.
    with pytest.raises(vladimir.InvalidNode):
        vladimir.validate_metadata()


@pytest.mark.skip("See Issue #1075")    # TODO: Issue #1075
def test_vladimir_invalidity_without_stake(testerchain, blockchain_ursulas, blockchain_alice):
    his_target = list(blockchain_ursulas)[4]
    vladimir = Vladimir.from_target_ursula(target_ursula=his_target)

    message = vladimir._signable_interface_info_message()
    signature = vladimir._crypto_power.power_ups(SigningPower).sign(vladimir.timestamp_bytes() + message)
    vladimir._Teacher__interface_signature = signature
    vladimir.substantiate_stamp(client_password=INSECURE_DEVELOPMENT_PASSWORD)

    # However, the actual handshake proves him wrong.
    with pytest.raises(vladimir.InvalidNode):
        vladimir.verify_node(blockchain_alice.network_middleware, certificate_filepath="doesn't matter")


@pytest.mark.skip("See Issue #1075")    # TODO: Issue #1075
def test_vladimir_uses_his_own_signing_key(blockchain_alice, blockchain_ursulas):
    """
    Similar to the attack above, but this time Vladimir makes his own interface signature
    using his own signing key, which he claims is Ursula's.
    """
    his_target = list(blockchain_ursulas)[4]
    vladimir = Vladimir.from_target_ursula(target_ursula=his_target)

    message = vladimir._signable_interface_info_message()
    signature = vladimir._crypto_power.power_ups(SigningPower).sign(vladimir.timestamp_bytes() + message)
    vladimir._Teacher__interface_signature = signature
    vladimir.substantiate_stamp(client_password=INSECURE_DEVELOPMENT_PASSWORD)

    vladimir._worker_is_bonded_to_staker = lambda: True
    vladimir._staker_is_really_staking = lambda: True
    vladimir.validate_worker()  # lol

    # With this slightly more sophisticated attack, his metadata does appear valid.
    vladimir.validate_metadata()

    # However, the actual handshake proves him wrong.
    with pytest.raises(vladimir.InvalidNode):
        vladimir.verify_node(blockchain_alice.network_middleware, certificate_filepath="doesn't matter")


# TODO: Change name of this file, extract this test
def test_blockchain_ursulas_reencrypt(blockchain_ursulas, blockchain_alice, blockchain_bob, policy_value):

    label = b'bbo'

    # TODO: Make sample selection buffer configurable - #1061
    # Currently, it only supports N<=6, since for N=7, it tries to sample 11 ursulas due to wiggle room,
    # and blockchain_ursulas only contains 10.
    # For N >= 7 : NotEnoughBlockchainUrsulas: Cannot create policy with 7 arrangements: There are 10 active stakers, need at least 11.
    m = n = 6
    expiration = maya.now() + datetime.timedelta(days=5)

    _policy = blockchain_alice.grant(bob=blockchain_bob,
                                     label=label,
                                     m=m,
                                     n=n,
                                     expiration=expiration,
                                     value=policy_value)

    enrico = Enrico.from_alice(blockchain_alice, label)

    message = b"Oh, this isn't even BO. This is beyond BO. It's BBO."

    message_kit, signature = enrico.encrypt_message(message)

    blockchain_bob.join_policy(label, bytes(blockchain_alice.stamp))

    plaintext = blockchain_bob.retrieve(message_kit, enrico, blockchain_alice.stamp, label)
    assert plaintext[0] == message
