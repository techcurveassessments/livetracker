# livetracker
# Live Assignment Submission Dashboard 📊

A real-time Streamlit dashboard for tracking and monitoring student assignment submissions stored in AWS S3. This application provides educators with an intuitive interface to view submission statistics, test results, and student progress.

## Features

- **Real-time Monitoring**: Auto-refreshes every 10 seconds to show latest submissions
- **Detailed Analytics**: View pass/fail rates, scores, and completion statistics
- **Date-based Grouping**: Submissions organized by submission date
- **Individual Student Details**: Drill down into specific question-level results
- **Export Functionality**: Download submission data as CSV files
- **Visual Status Indicators**: Color-coded status for quick assessment

## Prerequisites

- Python 3.7+
- AWS Account with S3 access
- AWS credentials configured

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd live-submission-tracker
```

2. Install required dependencies:
```bash
pip install streamlit boto3 pandas
```

3. Set up AWS credentials as environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
export AWS_DEFAULT_REGION=us-east-1  # Optional, defaults to us-east-1
```

## Configuration

### S3 Bucket Structure

The application expects submissions to be stored in S3 with the following structure:

```
ltisubmissions/
├── StudentName_YYYYMMDD_HHMMSS/
│   ├── q1/
│   │   └── test_report.log
│   ├── q2/
│   │   └── test_report.log
│   └── q3/
│       └── test_report.log
└── AnotherStudent_YYYYMMDD_HHMMSS/
    └── ...
```

### Test Report Format

Each `test_report.log` file should contain test results with:
- `[PASS]` markers for successful tests
- `[FAIL]` markers for failed tests

## Usage

1. Start the Streamlit application:
```bash
streamlit run app.py
```

2. Open your browser and navigate to `http://localhost:8501`

3. The dashboard will automatically load and display:
   - Overall statistics for each submission date
   - Individual student results
   - Question-level pass/fail details

## Dashboard Components

### Summary Metrics
- **Total Students**: Number of students who submitted
- **Average Score**: Mean score across all submissions
- **Perfect**: Count of students with all tests passing
- **Failed**: Count of students with failing submissions

### Student Details
Each student entry shows:
- **Name**: Extracted from folder name
- **Submission Time**: When the assignment was submitted
- **Score**: Total number of passed tests
- **Status**: Overall completion status with visual indicators
  - ✅ Perfect: All tests passed
  - ⚠️ Partial: Some tests passed
  - ❌ Failed: No tests passed or submission issues

### Question Breakdown
For each student, individual questions display:
- Question ID (q1, q2, etc.)
- Pass/fail counts
- Status indicator

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key | Required |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Required |
| `AWS_DEFAULT_REGION` | AWS region | `us-east-1` |

## Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   - Ensure environment variables are set correctly
   - Verify IAM permissions for S3 access

2. **No Data Displayed**
   - Check S3 bucket name (`BUCKET_NAME` variable)
   - Verify folder structure matches expected format
   - Ensure test_report.log files exist

3. **Parsing Errors**
   - Student folder names should follow: `Name_YYYYMMDD_HHMMSS` format
   - Question folders should be named `q1`, `q2`, etc.

### Required IAM Permissions

Your AWS credentials need the following S3 permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetObject"
            ],
            "Resource": [
                "arn:aws:s3:::ltisubmissions",
                "arn:aws:s3:::ltisubmissions/*"
            ]
        }
    ]
}
```

## Customization

### Changing Refresh Interval
Modify the `refresh_interval` variable (line 69) to adjust auto-refresh timing:
```python
refresh_interval = 30  # Refresh every 30 seconds
```

### Bucket Configuration
Update the `BUCKET_NAME` constant to use a different S3 bucket:
```python
BUCKET_NAME = "your-bucket-name"
```

## Export Features

- **CSV Download**: Export submission data for each date as CSV files
- **Data Format**: Includes student names, scores, timestamps, and status information

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review AWS S3 permissions
3. Verify data structure in S3 bucket
4. Open an issue in the repository

---

**Note**: This dashboard is designed for educational environments where student submissions are automatically uploaded to S3 with the expected folder structure and test report format.
