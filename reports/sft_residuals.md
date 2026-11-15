CyberSOS SFT residual gate

Target: revise route after an observed correction or provider failure
REVIEW bounded training allocation and additional B2 evaluation reservation before the optional pilot

Named sequential targets: {
  "revise route after an observed correction or provider failure": {
    "episodes": [
      "passkey_access_corrected",
      "phone_temporary_failure_retry"
    ],
    "independent_roots": [
      "passkey_access_corrected",
      "phone_temporary_failure_retry"
    ]
  }
}

Reserved B0/B1 evaluation seconds: 6117.929080017601
Any B2 sweep needs an additional measured reservation before training.
