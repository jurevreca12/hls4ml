from hls4ml.backends.backend import get_backend
from hls4ml.backends.oneapi.oneapi_template import StreamFunctionCallTemplate, TaskSequenceTemplate
from hls4ml.backends.template import FunctionCallTemplate, LayerConfigTemplate
from hls4ml.model.layers import Concatenate, Dot, Merge

# TODO - Very similar to vivado/merge_templates.py - only difference is on line 67:
# TODO -    get_backend('vivado').product_type(inp1.type.precision, inp2.type.precision)
# TODO - Look into ways of having passes similar accross many backends in a shared folder thorugh inheritance and overriding.

# Merge templates
merge_config_template = """struct config{index} : nnet::merge_config {{
    static const unsigned n_elem = {n_elem};
    static const unsigned reuse_factor = {reuse};
}};\n"""

merge_function_template = 'nnet::{merge}<{input1_t}, {input2_t}, {output_t}, {config}>({input1}, {input2}, {output});'

merge_task_sequence_template = (
    'task_sequence<nnet::{merge}_stream<{input1_pipe}, {input2_pipe}, {output_pipe}, {config}>> {name};'
)

merge_stream_function_template = '{name}.async();'

merge_include_list = ['nnet_utils/nnet_merge.h', 'nnet_utils/nnet_merge_stream.h']


class MergeConfigTemplate(LayerConfigTemplate):
    def __init__(self):
        super().__init__(Merge)
        self.template = merge_config_template

    def format(self, node):
        params = self._default_config_params(node)
        params['n_elem'] = node.get_input_variable(node.inputs[0]).size_cpp()

        return self.template.format(**params)


class MergeFunctionTemplate(FunctionCallTemplate):
    def __init__(self):
        super().__init__((Merge, Concatenate, Dot), include_header=merge_include_list)
        self.template = merge_function_template

    def format(self, node):
        params = self._default_function_params(node)
        params['merge'] = node.get_attr('op').lower()
        params['input1_t'] = node.get_input_variable(node.inputs[0]).type.name
        params['input2_t'] = node.get_input_variable(node.inputs[1]).type.name
        params['input1'] = node.get_input_variable(node.inputs[0]).name
        params['input2'] = node.get_input_variable(node.inputs[1]).name

        return self.template.format(**params)


class MergeTaskSequenceTemplate(TaskSequenceTemplate):
    def __init__(self):
        super().__init__((Merge, Concatenate, Dot))
        self.template = merge_task_sequence_template

    def format(self, node):
        params = self._default_function_params(node)
        params['merge'] = node.get_attr('op').lower()
        params['input1_pipe'] = node.get_input_variable(node.inputs[0]).pipe_name
        params['input2_pipe'] = node.get_input_variable(node.inputs[1]).pipe_name
        return self.template.format(**params)


class MergeStreamFunctionTemplate(StreamFunctionCallTemplate):
    def __init__(self):
        super().__init__((Merge, Concatenate, Dot))
        self.template = merge_stream_function_template

    def format(self, node):
        params = self._default_function_params(node)

        return self.template.format(**params)


# Dot templates
dot_config_template = """struct config{index} : nnet::dot_config {{
    static const unsigned n_in = {n_in};
    static const unsigned n_out = {n_out};

    static const unsigned reuse_factor = {reuse};

    typedef {accum_t.name} accum_t;

    template<class x_T, class y_T>
    using product = nnet::product::{product_type}<x_T, y_T>;
}};\n"""


class DotConfigTemplate(LayerConfigTemplate):
    def __init__(self):
        super().__init__(Dot)
        self.template = dot_config_template

    def format(self, node):
        inp1 = node.get_input_variable(node.inputs[0])
        inp2 = node.get_input_variable(node.inputs[1])
        params = self._default_config_params(node)
        params['n_out'] = 1
        params['n_in'] = inp1.shape[0]
        params['product_type'] = get_backend('oneAPI').product_type(inp1.type.precision, inp2.type.precision)

        return self.template.format(**params)


# Concatenate templates
concat_config_template = """struct config{index} : nnet::concat_config {{
    static const unsigned n_elem1_0 = {n_elem1_0};
    static const unsigned n_elem1_1 = {n_elem1_1};
    static const unsigned n_elem1_2 = {n_elem1_2};
    static const unsigned n_elem2_0 = {n_elem2_0};
    static const unsigned n_elem2_1 = {n_elem2_1};
    static const unsigned n_elem2_2 = {n_elem2_2};

    static const int axis = {axis};
}};\n"""


class ConcatenateConfigTemplate(LayerConfigTemplate):
    def __init__(self):
        super().__init__(Concatenate)
        self.template = concat_config_template

    def format(self, node):
        params = self._default_config_params(node)
        for i in range(3):
            params.setdefault(f'n_elem1_{i}', 0)
            params.setdefault(f'n_elem2_{i}', 0)
        inp1 = node.get_input_variable(node.inputs[0])
        inp2 = node.get_input_variable(node.inputs[1])
        for i, (s1, s2) in enumerate(zip(inp1.shape, inp2.shape)):
            params[f'n_elem1_{i}'] = s1
            params[f'n_elem2_{i}'] = s2

        return self.template.format(**params)
