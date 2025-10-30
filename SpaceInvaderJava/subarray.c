#include <stdio.h>

void visualizeKadane(int arr[], int n) {
    int max_current = arr[0];
    int max_global = arr[0];
    int start = 0, end = 0, s = 0;

    printf("\nStep-by-step Visualization:\n");
    printf("Index | Element | max_current | max_global | Subarray\n");
    printf("--------------------------------------------------------\n");

    for (int i = 0; i < n; i++) {
        if (i == 0) {
            printf("%5d | %7d | %12d | %10d | [%d]\n", i, arr[i], max_current, max_global, arr[i]);
            continue;
        }

        if (arr[i] > max_current + arr[i]) {
            max_current = arr[i];
            s = i;
        } else {
            max_current += arr[i];
        }

        if (max_current > max_global) {
            max_global = max_current;
            start = s;
            end = i;
        }

        printf("%5d | %7d | %12d | %10d | [", i, arr[i], max_current, max_global);
        for (int j = s; j <= i; j++) {
            printf("%d", arr[j]);
            if (j < i) printf(", ");
        }
        printf("]\n");
    }

    printf("\nFinal Maximum Subarray Sum = %d\n", max_global);
    printf("Final Subarray = [ ");
    for (int i = start; i <= end; i++) {
        printf("%d ", arr[i]);
    }
    printf("]\n");
}

int main() {
    int n;

    printf("Enter the number of elements: ");
    scanf("%d", &n);

    int arr[n];
    printf("Enter %d elements:\n", n);
    for (int i = 0; i < n; i++) {
        scanf("%d", &arr[i]);
    }

    visualizeKadane(arr, n);

    return 0;
}
