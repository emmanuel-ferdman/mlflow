import functools
import inspect
from typing import Any, Callable, Literal, Optional, Union

from pydantic import BaseModel

from mlflow.entities import Assessment, Feedback
from mlflow.entities.trace import Trace


class Scorer(BaseModel):
    name: str
    aggregations: Optional[list] = None

    def run(self, *, inputs=None, outputs=None, expectations=None, trace=None, **kwargs):
        from mlflow.evaluation import Assessment as LegacyAssessment

        merged = {
            "inputs": inputs,
            "outputs": outputs,
            "expectations": expectations,
            "trace": trace,
            **kwargs,
        }
        # Filter to only the parameters the function actually expects
        sig = inspect.signature(self.__call__)
        filtered = {k: v for k, v in merged.items() if k in sig.parameters}
        result = self(**filtered)
        if not (
            isinstance(result, (int, float, bool, str, Assessment, LegacyAssessment))
            or (
                isinstance(result, list)
                and all(isinstance(item, (Assessment, LegacyAssessment)) for item in result)
            )
        ):
            if isinstance(result, list) and len(result) > 0:
                result_type = "list[" + type(result[0]).__name__ + "]"
            else:
                result_type = type(result).__name__
            raise ValueError(
                f"{self.name} must return one of int, float, bool, str, "
                f"Assessment, or list[Assessment]. Got {result_type}"
            )
        return result

    def __call__(
        self,
        *,
        inputs: Any = None,
        outputs: Any = None,
        expectations: Optional[dict[str, Any]] = None,
        trace: Optional[Trace] = None,
        **kwargs,
    ) -> Union[int, float, bool, str, Feedback, list[Feedback]]:
        # TODO: make sure scorer's signature is simply equal to whatever keys are
        # in the eval dataset once we migrate from the agent eval harness
        # Currently, the evaluation harness only passes the following reserved
        # extra keyword arguments. This will be fully flexible once we migrate off
        # the agent eval harness.
        # - retrieved_context (optional): Retrieved context, can be from your
        #   input eval dataset or from trace
        # - custom_expected (optional): Custom expected results from input eval dataset
        # - custom_inputs (optional): Custom inputs from your input eval dataset
        # - custom_outputs (optional): Custom outputs from the agent's response
        # - tool_calls (optional): Tool calls from the agent's response.
        """
        Implement the custom scorer's logic here.


        The scorer will be called for each row in the input evaluation dataset.

        Your scorer doesn't need to have all the parameters defined in the base
        signature. You can define a custom scorer with only the parameters you need.
        See the parameter details below for what values are passed for each parameter.

        .. list-table::
            :widths: 20 20 20
            :header-rows: 1

            * - Parameter
              - Description
              - Source

            * - ``inputs``
              - A single input to the target model/app.
              - Derived from either dataset or trace.

                * When the dataset contains ``inputs`` column, the value will be
                  passed as is.
                * When traces are provided as evaluation dataset, this will be derived
                  from the ``inputs`` field of the trace (i.e. inputs captured as the
                  root span of the trace).

            * - ``outputs``
              - A single output from the target model/app.
              - Derived from either dataset, trace, or output of ``predict_fn``.

                * When the dataset contains ``outputs`` column, the value will be
                  passed as is.
                * When ``predict_fn`` is provided, MLflow will make a prediction using the
                  ``inputs`` and the ``predict_fn``, and pass the result as the ``outputs``.
                * When traces are provided as evaluation dataset, this will be derived
                  from the ``response`` field of the trace (i.e. outputs captured as the
                  root span of the trace).

            * - ``expectations``
              - Ground truth or any expectation for each prediction, e.g. expected retrieved docs.
              - Derived from either dataset or trace.

                * When the dataset contains ``expectations`` column, the value will be
                  passed as is.
                * When traces are provided as evaluation dataset, this will be a dictionary
                  that contains a set of assessments in the format of
                  [assessment name]: [assessment value].

            * - ``trace``
              - A trace object corresponding to the prediction for the row.
              - Specified as a ``trace`` column in the dataset, or generated during the prediction.

            * - ``**kwargs``
              - Additional keyword arguments passed to the scorer.
              - Must be specified as extra columns in the input dataset.

        Example:

            .. code-block:: python

                class NotEmpty(BaseScorer):
                    name = "not_empty"

                    def __call__(self, *, outputs) -> bool:
                        return outputs != ""


                class ExactMatch(BaseScorer):
                    name = "exact_match"

                    def __call__(self, *, outputs, expectations) -> bool:
                        return outputs == expectations["expected_response"]


                class NumToolCalls(BaseScorer):
                    name = "num_tool_calls"

                    def __call__(self, *, trace) -> int:
                        spans = trace.search_spans(name="tool_call")
                        return len(spans)


                # Use the scorer in an evaluation
                mlflow.genai.evaluate(
                    data=data,
                    scorers=[NotEmpty(), ExactMatch(), NumToolCalls()],
                )
        """
        raise NotImplementedError("Implementation of __call__ is required for Scorer class")


class BuiltInScorer(Scorer):
    def update_evaluation_config(evaluation_config) -> dict:
        """
        The builtin scorer will take in an evaluation_config and return an updated version
        of it as necessary to comply with the expected format for mlflow.evaluate().
        More details about built-in judges can be found at
        https://docs.databricks.com/aws/en/generative-ai/agent-evaluation/llm-judge-reference
        """
        raise NotImplementedError("Please use an instance of BuiltInScorer")


def scorer(
    func=None,
    *,
    name: Optional[str] = None,
    aggregations: Optional[
        list[Union[Literal["min", "max", "mean", "median", "variance", "p90", "p99"], Callable]]
    ] = None,
):
    """
    A decorator to define a custom scorer that can be used in ``mlflow.genai.evaluate()``.

    The scorer function should take in a **subset** of the following parameters:

    .. list-table::
        :widths: 20 20 20
        :header-rows: 1

        * - Parameter
          - Description
          - Source

        * - ``inputs``
          - A single input to the target model/app.
          - Derived from either dataset or trace.

            * When the dataset contains ``inputs`` column, the value will be passed as is.
            * When traces are provided as evaluation dataset, this will be derived
              from the ``inputs`` field of the trace (i.e. inputs captured as the
              root span of the trace).

        * - ``outputs``
          - A single output from the target model/app.
          - Derived from either dataset, trace, or output of ``predict_fn``.

            * When the dataset contains ``outputs`` column, the value will be passed as is.
            * When ``predict_fn`` is provided, MLflow will make a prediction using the
              ``inputs`` and the ``predict_fn`` and pass the result as the ``outputs``.
            * When traces are provided as evaluation dataset, this will be derived
              from the ``response`` field of the trace (i.e. outputs captured as the
              root span of the trace).

        * - ``expectations``
          - Ground truth or any expectation for each prediction e.g., expected retrieved docs.
          - Derived from either dataset or trace.

            * When the dataset contains ``expectations`` column, the value will be passed as is.
            * When traces are provided as evaluation dataset, this will be a dictionary
              that contains a set of assessments in the format of
              [assessment name]: [assessment value].

        * - ``trace``
          - A trace object corresponding to the prediction for the row.
          - Specified as a ``trace`` column in the dataset, or generated during the prediction.

        * - ``**kwargs``
          - Additional keyword arguments passed to the scorer.
          - Must be specified as extra columns in the input dataset.

    Example:

        .. code-block:: python

            from mlflow.genai.scorers import scorer


            @scorer
            def not_empty(outputs) -> bool:
                return outputs != ""


            @scorer
            def exact_match(outputs, expectations) -> bool:
                return outputs == expectations["expected_response"]


            @scorer
            def num_tool_calls(trace) -> int:
                spans = trace.search_spans(name="tool_call")
                return len(spans)


            # Use the scorer in an evaluation
            mlflow.genai.evaluate(
                data=data,
                scorers=[not_empty, exact_match, num_tool_calls],
            )
    """

    if func is None:
        return functools.partial(scorer, name=name, aggregations=aggregations)

    class CustomScorer(Scorer):
        def __call__(self, *args, **kwargs):
            return func(*args, **kwargs)

    # Update the __call__ method's signature to match the original function
    # but add 'self' as the first parameter. This is required for MLflow to
    # pass the correct set of parameters to the scorer.
    signature = inspect.signature(func)
    params = list(signature.parameters.values())
    new_params = [inspect.Parameter("self", inspect.Parameter.POSITIONAL_OR_KEYWORD)] + params
    new_signature = signature.replace(parameters=new_params)
    CustomScorer.__call__.__signature__ = new_signature

    return CustomScorer(
        name=name or func.__name__,
        aggregations=aggregations,
    )
