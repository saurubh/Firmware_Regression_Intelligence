from fri.utils.matching import keyword_in_text, path_matches


def test_me_does_not_match_memory():
    assert path_matches("Silicon/Me/Heci.c", "/me/")
    assert not path_matches("Silicon/Memory/MrcTrain.c", "/me/")
    assert not path_matches("Silicon/Memory/MrcTrain.c", "me")


def test_camel_case_and_segments():
    assert path_matches("MdeModulePkg/Universal/BdsDxe/BdsEntry.c", "bds")
    assert path_matches("Silicon/Memory/MrcTrain.c", "mrc")
    assert path_matches("Silicon/Memory/MrcTrain.c", "memory")
    assert not path_matches("SecurityPkg/Library/SecureBoot.c", "boot")


def test_pci_does_not_eat_pcie_without_own_token():
    assert path_matches("PcieBusDxe/PcieLink.c", "pcie")
    assert not path_matches("PcieBusDxe/PcieLink.c", "pci")


def test_secure_boot_spellings_are_equivalent():
    assert keyword_in_text("Enable SecureBoot policy", "SECURE BOOT")
    assert keyword_in_text("Enable Secure Boot policy", "SECUREBOOT")
    assert keyword_in_text("gBS->ExitBootServices", "EXITBOOTSERVICES")
