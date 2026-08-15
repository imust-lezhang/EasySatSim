import io


SIMPLE_CNN_INPUT_SHAPE = (3, 32, 32)
SIMPLE_CNN_HIDDEN_FEATURES = 256
SIMPLE_CNN_CLASS_NUMBER = 10
FLOAT32_BYTE_SIZE = 4


try:
    import torch
    import torch.nn as nn
except ModuleNotFoundError:
    torch = None
    nn = None


def require_torch():
    if torch is None or nn is None:
        raise ModuleNotFoundError(
            "Case 2 CNN model construction requires torch. "
            "Install PyTorch before training or serializing the model."
        )
    return torch, nn


if nn is not None:
    class SimpleCNN(nn.Module):
        def __init__(self):
            super(SimpleCNN, self).__init__()
            self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
            self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
            self.pool = nn.MaxPool2d(2, 2)
            self.fc1 = nn.Linear(64 * 8 * 8, SIMPLE_CNN_HIDDEN_FEATURES)
            self.fc2 = nn.Linear(SIMPLE_CNN_HIDDEN_FEATURES,
                                 SIMPLE_CNN_CLASS_NUMBER)
            self.relu = nn.ReLU()

        def forward(self, x):
            x = self.pool(self.relu(self.conv1(x)))
            x = self.pool(self.relu(self.conv2(x)))
            x = x.view(-1, 64 * 8 * 8)
            x = self.relu(self.fc1(x))
            x = self.fc2(x)
            return x
else:
    class SimpleCNN:
        def __init__(self):
            require_torch()


def conv2d_parameter_count(in_channels, out_channels, kernel_size, bias=True):
    kernel_parameters = out_channels * in_channels * kernel_size * kernel_size
    bias_parameters = out_channels if bias else 0
    return kernel_parameters + bias_parameters


def linear_parameter_count(in_features, out_features, bias=True):
    weight_parameters = in_features * out_features
    bias_parameters = out_features if bias else 0
    return weight_parameters + bias_parameters


def get_simple_cnn_parameter_breakdown():
    return {
        "conv1": conv2d_parameter_count(3, 32, 3),
        "conv2": conv2d_parameter_count(32, 64, 3),
        "fc1": linear_parameter_count(64 * 8 * 8, SIMPLE_CNN_HIDDEN_FEATURES),
        "fc2": linear_parameter_count(
            SIMPLE_CNN_HIDDEN_FEATURES,
            SIMPLE_CNN_CLASS_NUMBER,
        ),
    }


def get_simple_cnn_parameter_count():
    return sum(get_simple_cnn_parameter_breakdown().values())


def get_simple_cnn_raw_parameter_byte_size(dtype_byte_size=FLOAT32_BYTE_SIZE):
    return get_simple_cnn_parameter_count() * dtype_byte_size


def get_simple_cnn_spec_summary():
    return {
        "input_shape": SIMPLE_CNN_INPUT_SHAPE,
        "class_number": SIMPLE_CNN_CLASS_NUMBER,
        "parameter_breakdown": get_simple_cnn_parameter_breakdown(),
        "parameter_count": get_simple_cnn_parameter_count(),
        "raw_float32_parameter_bytes": get_simple_cnn_raw_parameter_byte_size(),
    }


def build_simple_cnn(device=None):
    require_torch()
    model = SimpleCNN()
    if device is not None:
        model = model.to(device)
    return model


def count_parameters(model, trainable_only=True):
    if trainable_only:
        return sum(parameter.numel() for parameter in model.parameters()
                   if parameter.requires_grad)
    return sum(parameter.numel() for parameter in model.parameters())


def describe_model(model=None):
    if model is None:
        model = build_simple_cnn()
    return {
        "model_name": model.__class__.__name__,
        "trainable_parameters": count_parameters(model, trainable_only=True),
        "all_parameters": count_parameters(model, trainable_only=False),
    }


def state_dict_to_bytes(state_dict):
    active_torch, _ = require_torch()
    buffer = io.BytesIO()
    active_torch.save(state_dict, buffer)
    return buffer.getvalue()


def get_state_dict_serialized_size(model=None):
    if model is None:
        model = build_simple_cnn()
    return len(state_dict_to_bytes(model.state_dict()))


def get_model_serialization_summary(model=None):
    if model is None:
        model = build_simple_cnn()
    summary = describe_model(model=model)
    summary["state_dict_serialized_size_byte"] = get_state_dict_serialized_size(
        model=model
    )
    return summary
