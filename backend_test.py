#!/usr/bin/env python3
import requests
import sys
import json
from datetime import datetime

class SaudiEquityAPITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Test data
        self.test_email = f"test_user_{datetime.now().strftime('%H%M%S')}@example.com"
        self.test_password = "TestPass123!"
        self.test_name = "Test User"

    def log_test(self, name, success, details="", error=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {error}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "error": error
        })

    def test_api_health(self):
        """Test if API is accessible"""
        try:
            response = requests.get(f"{self.api_url}/sectors", timeout=10)
            success = response.status_code in [200, 401]  # 401 is ok since we're not authenticated
            self.log_test("API Health Check", success, f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_test("API Health Check", False, error=str(e))
            return False

    def test_register(self):
        """Test user registration"""
        try:
            payload = {
                "email": self.test_email,
                "password": self.test_password,
                "name": self.test_name
            }
            response = requests.post(f"{self.api_url}/auth/register", json=payload, timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user", {}).get("id")
                details = f"User ID: {self.user_id}, Token received: {bool(self.token)}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
            
            self.log_test("User Registration", success, details)
            return success
        except Exception as e:
            self.log_test("User Registration", False, error=str(e))
            return False

    def test_login(self):
        """Test user login"""
        try:
            payload = {
                "email": self.test_email,
                "password": self.test_password
            }
            response = requests.post(f"{self.api_url}/auth/login", json=payload, timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                token = data.get("access_token")
                details = f"Login successful, Token received: {bool(token)}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
            
            self.log_test("User Login", success, details)
            return success
        except Exception as e:
            self.log_test("User Login", False, error=str(e))
            return False

    def test_profile(self):
        """Test get user profile"""
        if not self.token:
            self.log_test("User Profile", False, error="No token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.api_url}/auth/profile", headers=headers, timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                details = f"Profile: {data.get('name')} ({data.get('email')})"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
            
            self.log_test("User Profile", success, details)
            return success
        except Exception as e:
            self.log_test("User Profile", False, error=str(e))
            return False

    def test_seed_data(self):
        """Test data seeding"""
        if not self.token:
            self.log_test("Seed Data", False, error="No token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.post(f"{self.api_url}/seed-data", headers=headers, timeout=15)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                details = f"Seed result: {data.get('message', '')}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
            
            self.log_test("Seed Data", success, details)
            return success
        except Exception as e:
            self.log_test("Seed Data", False, error=str(e))
            return False

    def test_sectors(self):
        """Test get sectors"""
        try:
            response = requests.get(f"{self.api_url}/sectors", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                sectors = data.get("sectors", [])
                details = f"Found {len(sectors)} sectors: {sectors}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
            
            self.log_test("Get Sectors", success, details)
            return success, sectors if success else []
        except Exception as e:
            self.log_test("Get Sectors", False, error=str(e))
            return False, []

    def test_companies(self, sector=None):
        """Test get companies"""
        try:
            url = f"{self.api_url}/companies"
            if sector:
                url += f"?sector={sector}"
                
            response = requests.get(url, timeout=10)
            success = response.status_code == 200
            
            if success:
                companies = response.json()
                details = f"Found {len(companies)} companies" + (f" in {sector}" if sector else "")
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
            
            test_name = f"Get Companies{' (' + sector + ')' if sector else ''}"
            self.log_test(test_name, success, details)
            return success, companies if success else []
        except Exception as e:
            test_name = f"Get Companies{' (' + sector + ')' if sector else ''}"
            self.log_test(test_name, False, error=str(e))
            return False, []

    def test_company_detail(self, company_id):
        """Test get single company details"""
        try:
            response = requests.get(f"{self.api_url}/companies/{company_id}", timeout=10)
            success = response.status_code == 200
            
            if success:
                company = response.json()
                details = f"Company: {company.get('name')} ({company.get('sector')})"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
            
            self.log_test("Get Company Detail", success, details)
            return success, company if success else {}
        except Exception as e:
            self.log_test("Get Company Detail", False, error=str(e))
            return False, {}

    def test_analysis_calculation(self, company_id):
        """Test investment analysis calculation"""
        if not self.token:
            self.log_test("Analysis Calculation", False, error="No token available")
            return False, {}
            
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            payload = {
                "investment_usd": 1000000,
                "exit_year": 5,
                "company_id": company_id
            }
            
            response = requests.post(f"{self.api_url}/analysis/calculate", 
                                   json=payload, headers=headers, timeout=15)
            success = response.status_code == 200
            
            if success:
                analysis = response.json()
                details = f"NPV: {analysis.get('npv', 0):,.0f} SAR, IRR: {analysis.get('irr', 0)*100:.2f}%"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
            
            self.log_test("Analysis Calculation", success, details)
            return success, analysis if success else {}
        except Exception as e:
            self.log_test("Analysis Calculation", False, error=str(e))
            return False, {}

    def test_save_analysis(self, analysis_data):
        """Test save analysis"""
        if not self.token or not analysis_data:
            self.log_test("Save Analysis", False, error="No token or analysis data available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            payload = {"analysis": analysis_data}
            
            response = requests.post(f"{self.api_url}/analysis/save", 
                                   json=payload, headers=headers, timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                details = f"Analysis saved with ID: {data.get('id', 'unknown')}"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
            
            self.log_test("Save Analysis", success, details)
            return success
        except Exception as e:
            self.log_test("Save Analysis", False, error=str(e))
            return False

    def test_analysis_history(self):
        """Test get analysis history"""
        if not self.token:
            self.log_test("Analysis History", False, error="No token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.api_url}/analysis/history", headers=headers, timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                analyses = data.get("analyses", [])
                details = f"Found {len(analyses)} saved analyses"
            else:
                details = f"Status: {response.status_code}, Response: {response.text[:200]}"
            
            self.log_test("Analysis History", success, details)
            return success
        except Exception as e:
            self.log_test("Analysis History", False, error=str(e))
            return False

    def test_excel_export(self, analysis_id):
        """Test Excel export"""
        if not self.token or not analysis_id:
            self.log_test("Excel Export", False, error="No token or analysis ID available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            response = requests.get(f"{self.api_url}/analysis/{analysis_id}/export-excel", 
                                  headers=headers, timeout=15)
            success = response.status_code == 200 and 'application' in response.headers.get('content-type', '')
            
            if success:
                content_length = len(response.content)
                details = f"Excel file generated, size: {content_length} bytes"
            else:
                details = f"Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'unknown')}"
            
            self.log_test("Excel Export", success, details)
            return success
        except Exception as e:
            self.log_test("Excel Export", False, error=str(e))
            return False

    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting Saudi Equity Investment Dashboard API Tests\n")
        
        # Basic connectivity
        if not self.test_api_health():
            print("❌ API not accessible, stopping tests")
            return self.generate_report()
        
        # Authentication tests
        if not self.test_register():
            print("❌ Registration failed, stopping tests")
            return self.generate_report()
        
        if not self.test_login():
            print("⚠️  Login test failed, but continuing with registration token")
        
        if not self.test_profile():
            print("❌ Profile test failed, stopping tests")
            return self.generate_report()
        
        # Data seeding
        self.test_seed_data()
        
        # Data retrieval tests
        sectors_success, sectors = self.test_sectors()
        if not sectors_success or not sectors:
            print("❌ No sectors available, skipping company tests")
            return self.generate_report()
        
        # Test companies for first sector
        first_sector = sectors[0] if sectors else None
        if first_sector:
            companies_success, companies = self.test_companies(first_sector)
            
            if companies_success and companies:
                # Test company detail
                first_company = companies[0]
                company_id = first_company.get('id')
                
                if company_id:
                    self.test_company_detail(company_id)
                    
                    # Test analysis calculation
                    calc_success, analysis_data = self.test_analysis_calculation(company_id)
                    
                    if calc_success and analysis_data:
                        # Test save analysis
                        if self.test_save_analysis(analysis_data):
                            # Test history
                            self.test_analysis_history()
                            
                            # Test Excel export
                            analysis_id = analysis_data.get('id')
                            if analysis_id:
                                self.test_excel_export(analysis_id)
        
        return self.generate_report()

    def generate_report(self):
        """Generate test report"""
        print(f"\n📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("✅ All tests passed!")
            return 0
        else:
            print("❌ Some tests failed")
            failed_tests = [r for r in self.test_results if not r['success']]
            print("\nFailed tests:")
            for test in failed_tests:
                print(f"  • {test['test']}: {test['error']}")
            return 1

def main():
    tester = SaudiEquityAPITester()
    return tester.run_comprehensive_test()

if __name__ == "__main__":
    sys.exit(main())