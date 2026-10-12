document.addEventListener('DOMContentLoaded', function () {
    const pointsField = document.getElementById('id_pension_points');
    const pointValueField = document.getElementById('id_point_value');
    const grossField = document.getElementById('id_gross_payout_amount');
    const deductionField = document.getElementById('id_social_deduction_rate');
    const netField = document.getElementById('id_expected_payout_at_retirement');
    const typeField = document.getElementById('id_pension_type');

    function calculateGross() {
        if (!typeField || typeField.value === 'statutory') {
            const points = parseFloat(pointsField ? pointsField.value.replace(',', '.') : NaN);
            const val = parseFloat(pointValueField ? pointValueField.value.replace(',', '.') : NaN);
            if (!isNaN(points) && !isNaN(val) && grossField) {
                const computedGross = (points * val).toFixed(2);
                grossField.value = computedGross;
                calculateNet();
            }
        }
    }

    function calculateNet() {
        if (grossField && netField) {
            const gross = parseFloat(grossField.value.replace(',', '.'));
            const deduction = parseFloat(deductionField ? deductionField.value.replace(',', '.') : 0);
            if (!isNaN(gross) && !isNaN(deduction)) {
                const rate = deduction / 100.0;
                const computedNet = (gross * (1.0 - rate)).toFixed(2);
                netField.value = computedNet;
            }
        }
    }

    if (pointsField) {
        pointsField.addEventListener('blur', calculateGross);
    }
    if (pointValueField) {
        pointValueField.addEventListener('blur', calculateGross);
    }
    if (grossField) {
        grossField.addEventListener('blur', calculateNet);
    }
    if (deductionField) {
        deductionField.addEventListener('blur', calculateNet);
    }
});
