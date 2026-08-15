import csv
from pathlib import Path

from cases.case2.experiment.data.cifar10_data import resolve_case2_path


CL_COMMUNICATION_TITLE_ROW = [
    "Simulation_Time",
    "Architecture",
    "Event_Type",
    "Cumulative_Samples",
    "Entity_ID",
    "Source_IP",
    "Target_IP",
    "Sample_Index",
    "Label",
    "Payload_Byte",
    "Network_Counted_Byte",
]

CL_LEARNING_TITLE_ROW = [
    "Simulation_Time",
    "Architecture",
    "Train_Round",
    "Received_Samples_Total",
    "Used_Samples",
    "Remaining_Buffered_Samples",
    "Train_Loss",
    "Test_Accuracy",
]

FL_COMMUNICATION_TITLE_ROW = [
    "Simulation_Time",
    "Architecture",
    "Event_Type",
    "Round_ID",
    "User_ID",
    "Source_IP",
    "Target_IP",
    "Payload_Byte",
    "Network_Counted_Byte",
]

FL_LEARNING_TITLE_ROW = [
    "Simulation_Time",
    "Architecture",
    "Round_ID",
    "Selected_Clients",
    "Received_Updates",
    "Aggregation_Reason",
    "Test_Accuracy",
]


def reset_case2_event_logs(*file_paths):
    for file_path in file_paths:
        resolved_path = resolve_case2_path(file_path)
        if resolved_path.exists():
            resolved_path.unlink()
    return


def log_cl_communication_event(simulation_time, event_type, cumulative_samples,
                               entity_id, source_ip, target_ip, sample_index,
                               label, payload_byte, network_counted_byte):
    from configuration import simulation_config as cg

    append_csv_row(
        file_path=cg.COMMUNICATION_EVENTS_FILE_PATH,
        title_row=CL_COMMUNICATION_TITLE_ROW,
        row=[
            simulation_time,
            "cl",
            event_type,
            cumulative_samples,
            entity_id,
            source_ip,
            target_ip,
            sample_index,
            label,
            payload_byte,
            network_counted_byte,
        ],
    )
    return


def log_cl_learning_metric(simulation_time, train_round,
                           received_samples_total, used_samples,
                           remaining_buffered_samples, train_loss,
                           test_accuracy):
    from configuration import simulation_config as cg

    append_csv_row(
        file_path=cg.LEARNING_METRICS_FILE_PATH,
        title_row=CL_LEARNING_TITLE_ROW,
        row=[
            simulation_time,
            "cl",
            train_round,
            received_samples_total,
            used_samples,
            remaining_buffered_samples,
            train_loss,
            test_accuracy,
        ],
    )
    return


def log_fl_communication_event(simulation_time, event_type, round_id, user_id,
                               source_ip, target_ip, payload_byte,
                               network_counted_byte):
    from configuration import simulation_config as cg

    append_csv_row(
        file_path=cg.COMMUNICATION_EVENTS_FILE_PATH,
        title_row=FL_COMMUNICATION_TITLE_ROW,
        row=[
            simulation_time,
            "fl",
            event_type,
            round_id,
            user_id,
            source_ip,
            target_ip,
            payload_byte,
            network_counted_byte,
        ],
    )
    return


def log_fl_learning_metric(simulation_time, round_id, selected_clients,
                           received_updates, aggregation_reason,
                           test_accuracy):
    from configuration import simulation_config as cg

    append_csv_row(
        file_path=cg.LEARNING_METRICS_FILE_PATH,
        title_row=FL_LEARNING_TITLE_ROW,
        row=[
            simulation_time,
            "fl",
            round_id,
            selected_clients,
            received_updates,
            aggregation_reason,
            test_accuracy,
        ],
    )
    return


def append_csv_row(file_path, title_row, row):
    resolved_path = resolve_case2_path(file_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    write_title = not resolved_path.exists() or resolved_path.stat().st_size == 0
    with open(resolved_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if write_title:
            writer.writerow(title_row)
        writer.writerow(row)
    return resolved_path


def case2_file_exists(file_path):
    return Path(resolve_case2_path(file_path)).exists()
