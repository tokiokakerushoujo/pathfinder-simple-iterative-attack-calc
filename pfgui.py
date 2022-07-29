from random import randint
from typing import Dict, List
import dearpygui.dearpygui as dpg


def main():
    dpg.create_context()
    dpg.create_viewport(title='Custom Title', width=800, height=600)

    with dpg.value_registry():
        dpg.add_string_value(default_value="Class", tag="player_class")
        dpg.add_int_value(default_value=1, tag="number_atks")
        dpg.add_int_value(default_value=-5, tag="iterative_penalty")
        dpg.add_int_value(default_value=0, tag="ignore_penalty_on")

    modifiers = []

    with dpg.window(label="Pathfinding", tag="default"):
        with dpg.group():
            number_atks_input = dpg.add_input_int(
                label="Number of Attacks",
                source="number_atks",
                min_value=1
            )

        with dpg.group(show=False) as iterative_group:
            iterative_penalty_input = dpg.add_input_int(
                label="Iterative Attack Penalty", source="iterative_penalty")
            ignore_penalty_on_input = dpg.add_input_int(
                label="Ignore penalty on first [x] attacks",
                source="ignore_penalty_on", min_value=0)

        with dpg.group():
            crit_range_min_input = dpg.add_input_int(
                label="Minimum roll to threaten a Crit", default_value=20)
            crit_confirm_bonus_input = dpg.add_input_int(
                label="Bonus to confirm, if any", default_value=0, indent=25, )

        with dpg.group() as attack_group:
            attack_bonus_input = dpg.add_input_int(label="Base Attack Bonus")
            with dpg.group(horizontal=True) as atk_mod_button_grp:
                add_atk_mod_button = dpg.add_button(label="Add modifier")
                remove_atk_mod_button = dpg.add_button(
                    label="Remove last modifier", show=False)

        with dpg.group():
            enemy_ac_input = dpg.add_input_int(label="Enemy AC")

        roll_button = dpg.add_button(label="Roll!")

        results_group = dpg.add_group()

    def create_results_row(roll: int = 1, total: int = 1, hit: bool = False, crit: bool = False, crit_threat: bool = False, crit_confirm: Dict = {}):
        with dpg.group(parent=results_group) as roll_group:
            dpg.add_text(
                f"Attack: {'CRIT' if crit else 'HIT' if hit else 'MISS'}")
            dpg.add_text(f"{roll} => {total}", indent=50)
            if crit_threat and hit:
                dpg.add_text(
                    f"Confirm: {crit_confirm['roll']} => {crit_confirm['total_roll']} {'CONFIRM' if crit_confirm['hit'] else 'MISS'}", indent=50)

        return roll_group

    def result_to_row(result):
        return create_results_row(
            roll=result["roll"],
            total=result["total_roll"],
            hit=result["hit"],
            crit=result["crit"] if "crit" in result else False,
            crit_threat=result["crit_threat"],
            crit_confirm=result["crit_confirm"] if "crit_confirm" in result else {
            }
        )

    results_rows = []

    def clear_results():
        results_length = len(results_rows)
        for _ in range(results_length):
            dpg.delete_item(results_rows.pop())

    def gather_results():
        number_atks = dpg.get_value(number_atks_input)
        iterative_penalty = dpg.get_value(iterative_penalty_input)
        ignore_penalty = dpg.get_value(ignore_penalty_on_input)
        crit_range = dpg.get_value(crit_range_min_input)
        crit_confirm_bonus = dpg.get_value(crit_confirm_bonus_input)
        bab = dpg.get_value(attack_bonus_input)
        target_ac = dpg.get_value(enemy_ac_input)
        mod_value_input_list = list(map(lambda tuple: tuple[1], modifiers))
        atk_modifiers = dpg.get_values(mod_value_input_list)

        atk_bonus = sum(atk_modifiers) + bab
        results = calculate_results(
            num_attacks=number_atks,
            iterative_penalty=iterative_penalty,
            crit=crit_range,
            confirm_bonus=crit_confirm_bonus,
            atk_bonus=atk_bonus,
            enemy_ac=target_ac,
            ignore_penalty_on_first=ignore_penalty,
        )

        clear_results()
        for result in results:
            results_rows.append(result_to_row(result))

        dpg.show_item(results_group)

    def show_iterative_penalty_cb(sender, app_data, user_data):
        if app_data > 1:
            dpg.show_item(iterative_group)
        else:
            dpg.hide_item(iterative_group)

    def create_modifier_input():
        with dpg.group(horizontal=True, parent=attack_group) as mod_input:
            dpg.add_text(f"Modifier {len(modifiers)+1}:")
            dpg.add_input_text(width=400)
            new_mod_val = dpg.add_input_int(width=200)
        return (mod_input, new_mod_val)

    def add_atk_mod_cb(sender, app_data, user_data):
        modifiers.append(create_modifier_input())
        dpg.show_item(remove_atk_mod_button)

    def remove_atk_mod_cb(sender, app_data, user_data):
        if len(modifiers) < 1:
            dpg.hide_item(remove_atk_mod_button)
            return
        dpg.delete_item(modifiers.pop()[0])
        if len(modifiers) < 1:
            dpg.hide_item(remove_atk_mod_button)

    dpg.set_item_callback(number_atks_input, show_iterative_penalty_cb)
    dpg.set_item_callback(add_atk_mod_button, add_atk_mod_cb)
    dpg.set_item_callback(remove_atk_mod_button, remove_atk_mod_cb)
    dpg.set_item_callback(roll_button, gather_results)

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("default", True)
    dpg.start_dearpygui()
    dpg.destroy_context()


def get_attack_result(bonus: int, crit: int, enemy_ac: int):
    """Roll an attack against an enemy.

    Args:
        bonus (int): Total bonus to the attack roll.
        crit (int): Minimum roll to crit
        enemy_ac (int): Enemy AC to roll against

    Returns:
        result: { roll, total_roll = roll + attack, crit_threat: bool, hit: bool }
    """
    roll = randint(1, 20)
    return {
        "roll": roll,
        "total_roll": roll + bonus,
        "crit_threat": roll == 20 or roll >= crit,
        "hit": (roll + bonus) > enemy_ac
    }


def calculate_results(
    num_attacks: int = 1, iterative_penalty: int = -5,
    crit: int = 20, confirm_bonus: int = 0,
    atk_bonus: int = 0,
    enemy_ac: int = 15,
    ignore_penalty_on_first: int = 0
) -> List[Dict]:
    """Perform a set of normal iterative attacks.

    Args:
        num_attacks (int, optional): Total number of attacks in round. Defaults to 1.
        iterative_penalty (int, optional): Penalty per iterative attack. Defaults to -5.
        crit (int, optional): Minimum roll to threaten a critical hit. Defaults to 20.
        confirm_bonus (int, optional): Bonuses to rolls attempting to confirm a crit. Defaults to 0.
        atk_bonus (int, optional): Bonuses on the attack roll to hit. Defaults to 0.
        enemy_ac (int, optional): AC to try to hit. Defaults to 15.
        ignore_penalty_on_first (int, optional): If affected by haste or similar, ignore the penalty on the first N attacks. Defaults to 0.

    Returns:
        List[Dict]: A List of attack results, as from get_attack_result.
    """
    results = []
    for atk in range(num_attacks):
        bonus = atk_bonus + ((atk-ignore_penalty_on_first) *
                             iterative_penalty) if atk > ignore_penalty_on_first-1 else atk_bonus
        result = get_attack_result(bonus, crit, enemy_ac)
        if result["crit_threat"] and result["hit"]:
            result["crit_confirm"] = get_attack_result(
                bonus + confirm_bonus, crit, enemy_ac)
            result["crit"] = result["hit"] and result["crit_confirm"]["hit"]
        results.append(result)
    return results


if __name__ == "__main__":
    main()
