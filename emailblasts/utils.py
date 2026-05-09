def email_blast_full_body(body, target_description):
    return "\n\n".join(
        [
            "Hi {{ first_name }},",
            f"<i><small>{email_blast_target_reason(target_description)}</small></i>",
            body.strip(),
            "**Philly Bike Action**",
        ]
    )


def email_blast_target_reason(target_description):
    reason = target_description.strip().rstrip(".")
    if not reason:
        reason = "match the selected audience"

    lower_reason = reason.lower()
    if lower_reason.startswith("you are receiving this email because"):
        return f"{reason}."
    if lower_reason.startswith("because "):
        return f"You are receiving this email {reason}."
    if lower_reason.startswith("you "):
        return f"You are receiving this email because {reason}."
    return f"You are receiving this email because you {reason}."
