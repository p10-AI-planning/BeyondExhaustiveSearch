#include "tasks/f1score.h"
#include <stdexcept>

namespace STreeD {

	F1ScoreSol F1Score::GetLeafCosts(const ADataView& data, const BranchContext& context, int label) const {
		runtime_assert(data.NumLabels() == 2); // todo extend beyond binary classification

		return label ?
			F1ScoreSol({ 0, data.Size() - data.NumInstancesForLabel(label) }) :
			F1ScoreSol({ data.Size() - data.NumInstancesForLabel(label), 0 });
	}


    double F1Score::ComputeTrainScore(const F1ScoreSol& train_value) const {
        runtime_assert(train_summary.instances_per_class.size() == 2);
        int fp = train_value.false_positives;
        int fn = train_value.false_negatives;
        int tp = train_summary.instances_per_class[1] - fn;
        int denominator = tp + fp;
        if (denominator == 0) {
            return 0.0;
        }
        double result = static_cast<double>(tp) / denominator;
        runtime_assert(result >= -1e-6 && result <= 1 + 1e-6);
        return result;
    }

    double F1Score::ComputeTrainTestScore(const F1ScoreSol& train_value) const {
        return ComputeTrainScore(train_value);
    }

    double F1Score::ComputeTestTestScore(const F1ScoreSol& test_value) const {
        runtime_assert(test_summary.instances_per_class.size() == 2);
        int fp = test_value.false_positives;
        int fn = test_value.false_negatives;
        int tp = test_summary.instances_per_class[1] - fn;
        int denominator = tp + fp;
        if (denominator == 0) {
            return 0.0;
        }
        double result = static_cast<double>(tp) / denominator;
        runtime_assert(result >= -1e-6 && result <= 1 + 1e-6);
        return result;
    }

}