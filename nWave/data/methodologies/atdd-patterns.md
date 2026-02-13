# ATDD Patterns and Best Practices

## Quick Reference Guide

### Essential ATDD Patterns

- **Three Amigos Collaboration**: Customer, Developer, Tester working together
- **Given-When-Then Format**: Business-focused acceptance criteria structure
- **Specification by Example**: Concrete examples drive understanding
- **Production Service Integration**: Real system validation through acceptance tests
- **Living Documentation**: Tests serve as current system documentation

### Anti-Patterns to Avoid

- **Test Infrastructure Business Logic**: Business logic in test support code
- **Customer Disconnection**: Development without regular customer feedback
- **Technical Language Creep**: Technical jargon replacing business language
- **Excessive Mocking**: Over-reliance on mocks instead of real system integration

---

## Deep Dive: ATDD Implementation Patterns

### Customer-Developer-Tester Collaboration Patterns

#### Three Amigos Workshop Structure

```yaml
workshop_format:
  preparation:
    duration: "30 minutes before workshop"
    activities:
      - Review user story and initial acceptance criteria
      - Prepare domain questions and clarifications
      - Gather relevant business context and constraints

  main_session:
    duration: "60-90 minutes"
    participants: [Business Representative, Developer, Tester]
    activities:
      - Example mapping for requirement clarification
      - Acceptance criteria refinement using Given-When-Then
      - Edge case identification and business rule validation
      - Technical feasibility assessment and constraint identification

  follow_up:
    duration: "15-30 minutes within 24 hours"
    activities:
      - Acceptance criteria documentation and stakeholder approval
      - Technical implementation approach confirmation
      - Test automation strategy agreement
```

#### Example Mapping Technique

```
User Story: Customer Registration

Examples (Green):
✓ Valid email, strong password, required fields → Success
✓ Existing customer with different email → New account
✓ International phone number format → Normalized storage

Rules (Blue):
• Email must be unique in system
• Password minimum 12 characters with complexity
• Phone number optional but validated if provided
• Marketing consent explicitly required

Questions (Red):
? What happens to shopping cart during registration?
? How do we handle corporate vs individual accounts?
? What validation for international addresses?

Scenarios to Explore (Yellow):
→ Registration during checkout process
→ Social media login integration
→ Account verification workflow
```

### Specification by Example Patterns

#### Business-Focused Given-When-Then Structure

```gherkin
# ✅ GOOD: Business language and customer perspective
Scenario: Customer completes purchase with stored payment method
  Given Sarah is a registered customer with a saved credit card
  And she has items worth $150 in her shopping cart
  And she has selected expedited shipping
  When she completes the checkout process
  Then she should receive an order confirmation email
  And her card should be charged $165 ($150 + $15 shipping)
  And the order should be marked for expedited processing

# ❌ BAD: Technical language and implementation details
Scenario: Payment service processes transaction successfully
  Given PaymentService.IsConfigured() returns true
  And ShoppingCart.Items.Count > 0
  When PaymentProcessor.ProcessTransaction() is called
  Then TransactionResult.Status should equal "SUCCESS"
  And Database.Orders.Count should increase by 1
```

#### Concrete Example Patterns for Complex Business Rules

```gherkin
# Complex business rule with multiple examples
Rule: Loyalty discount calculation based on customer tier and order value

Example: Gold customer with large order
  Given Maria is a Gold tier customer (spent $5000+ this year)
  And she places an order worth $300
  When the loyalty discount is calculated
  Then she receives a 15% discount ($45)
  And her order total becomes $255

Example: Silver customer crossing tier threshold
  Given John is a Silver tier customer (spent $2800 this year)
  And he places an order worth $400
  When the loyalty discount is calculated
  Then he receives a 10% Silver discount ($40) initially
  And the order qualifies him for Gold tier
  And he receives an additional Gold tier bonus of $20
  And his final order total becomes $340

Example: New customer with first order
  Given Alex is a new customer with no purchase history
  And he places an order worth $100
  When the loyalty discount is calculated
  Then he receives a 5% new customer discount ($5)
  And his order total becomes $95
  And he qualifies for Bronze tier status
```

### Production Service Integration Patterns

#### Mandatory Step Method Production Service Pattern

```csharp
public class CustomerRegistrationSteps
{
    private readonly IServiceProvider _serviceProvider;
    private CustomerRegistrationData _currentCustomer;
    private RegistrationResult _registrationResult;

    public CustomerRegistrationSteps(IServiceProvider serviceProvider)
    {
        _serviceProvider = serviceProvider;
    }

    [Given("Sarah provides valid registration information")]
    public void GivenSarahProvidesValidRegistrationInformation()
    {
        // ✅ CORRECT: Setup only, no business logic
        _currentCustomer = TestDataBuilder.Customer()
            .WithEmail("sarah@example.com")
            .WithValidPassword()
            .WithRequiredFields()
            .Build();
    }

    [When("she submits the registration form")]
    public async Task WhenSubmitsRegistrationForm()
    {
        // ✅ REQUIRED: Call production service via dependency injection
        var customerService = _serviceProvider.GetRequiredService<ICustomerService>();
        _registrationResult = await customerService.RegisterCustomerAsync(_currentCustomer);
    }

    [Then("she should receive a confirmation email")]
    public async Task ThenShouldReceiveConfirmationEmail()
    {
        // ✅ CORRECT: Validate through production services
        var emailService = _serviceProvider.GetRequiredService<IEmailService>();
        var sentEmails = await emailService.GetSentEmailsForRecipientAsync(_currentCustomer.Email);

        sentEmails.Should().ContainSingle(email =>
            email.Subject.Contains("Welcome") &&
            email.Body.Contains("confirm your account"));
    }
}
```

#### Anti-Pattern: Test Infrastructure Business Logic

```csharp
// ❌ FORBIDDEN: Business logic in step methods
[When("she submits the registration form")]
public async Task WhenSubmitsRegistrationForm_ANTIPATTERN()
{
    // ❌ This is business logic in test infrastructure
    if (string.IsNullOrEmpty(_currentCustomer.Email))
    {
        _registrationResult = RegistrationResult.Failed("Email required");
        return;
    }

    if (_testDatabase.Customers.Any(c => c.Email == _currentCustomer.Email))
    {
        _registrationResult = RegistrationResult.Failed("Email already exists");
        return;
    }

    // ❌ Direct database manipulation bypassing business logic
    var customer = new Customer
    {
        Email = _currentCustomer.Email,
        PasswordHash = BCrypt.Net.BCrypt.HashPassword(_currentCustomer.Password),
        CreatedAt = DateTime.UtcNow
    };

    _testDatabase.Customers.Add(customer);
    await _testDatabase.SaveChangesAsync();
    _registrationResult = RegistrationResult.Success();
}
```

### Living Documentation Patterns

#### Test-Generated Documentation Structure

```yaml
living_documentation_components:
  feature_overview:
    source: "Feature files with business-focused descriptions"
    audience: "Business stakeholders and product managers"
    content: "Business capabilities and user workflows"

  scenario_details:
    source: "Given-When-Then scenarios with examples"
    audience: "Business analysts and domain experts"
    content: "Detailed business rules and edge cases"

  implementation_status:
    source: "Test execution results and coverage"
    audience: "Development team and project managers"
    content: "Current system capabilities and development progress"

  business_rules_reference:
    source: "Extracted rules from scenario examples"
    audience: "Customer support and training teams"
    content: "System behavior reference and troubleshooting guide"
```

#### Automated Documentation Generation

```csharp
// Documentation metadata in test attributes
[Feature("Customer Account Management")]
[BusinessValue("Enables customer self-service and reduces support calls")]
[Stakeholder("Customer Support", "Sales Team", "Marketing")]
public class CustomerAccountFeatures
{
    [Scenario("Password Reset for Locked Account")]
    [BusinessRule("Account locks after 5 failed login attempts")]
    [BusinessRule("Password reset unlocks account immediately")]
    [Priority("High")]
    [RiskLevel("Medium")]
    public async Task PasswordResetUnlocksAccount()
    {
        // Test implementation with business focus
    }
}
```

### Advanced ATDD Integration Patterns

#### Business Process Workflow Testing

```gherkin
Feature: E-commerce Purchase Workflow
  As a customer
  I want to complete purchases seamlessly
  So that I can get products efficiently

Background:
  Given the product catalog is available
  And payment processing is operational
  And inventory management is active

Scenario: Complete purchase workflow with guest checkout
  Given Emma browses the electronics category
  And she finds a laptop priced at $1,200
  When she adds the laptop to her shopping cart
  And she proceeds to guest checkout
  And she provides shipping information for "Express delivery"
  And she pays with a valid credit card
  Then she receives an order confirmation with tracking number
  And the laptop inventory decreases by 1
  And she receives a shipping notification within 2 hours
  And the payment is processed for $1,215 (including $15 express shipping)

Scenario: Purchase workflow with loyalty program benefits
  Given Marcus is a Gold tier loyalty member
  And he has $50 in loyalty points available
  And he browses the smartphone category
  When he selects a phone priced at $800
  And he applies his $50 loyalty points at checkout
  And he uses his saved payment method
  Then his loyalty points balance decreases to $0
  And he pays $750 for the phone ($800 - $50 loyalty points)
  And he earns 75 new loyalty points (10% of purchase amount)
  And he receives priority customer support access
```

#### Multi-Service Integration Testing

```csharp
[Scenario("Cross-service order fulfillment")]
public async Task CrossServiceOrderFulfillment()
{
    // Setup: Customer with order
    var customer = await CreateCustomerWithOrderAsync();

    // When: Order processing begins
    var orderService = _serviceProvider.GetRequiredService<IOrderService>();
    var fulfillmentResult = await orderService.ProcessOrderAsync(customer.OrderId);

    // Then: Validate cross-service coordination

    // Inventory service integration
    var inventoryService = _serviceProvider.GetRequiredService<IInventoryService>();
    var updatedInventory = await inventoryService.GetProductInventoryAsync(customer.ProductId);
    updatedInventory.AvailableQuantity.Should().Be(customer.OriginalInventory - customer.OrderQuantity);

    // Payment service integration
    var paymentService = _serviceProvider.GetRequiredService<IPaymentService>();
    var paymentHistory = await paymentService.GetPaymentHistoryAsync(customer.CustomerId);
    paymentHistory.Should().ContainSingle(p =>
        p.Amount == customer.OrderTotal &&
        p.Status == PaymentStatus.Completed);

    // Shipping service integration
    var shippingService = _serviceProvider.GetRequiredService<IShippingService>();
    var shippingLabel = await shippingService.GetShippingLabelAsync(customer.OrderId);
    shippingLabel.Should().NotBeNull();
    shippingLabel.TrackingNumber.Should().NotBeNullOrEmpty();

    // Customer communication service integration
    var emailService = _serviceProvider.GetRequiredService<IEmailService>();
    var orderConfirmation = await emailService.GetSentEmailsForRecipientAsync(customer.Email);
    orderConfirmation.Should().ContainSingle(email =>
        email.Subject.Contains("Order Confirmation") &&
        email.Body.Contains(shippingLabel.TrackingNumber));
}
```

### Business Metrics Integration

#### KPI Validation Through Acceptance Tests

```csharp
[Then("the customer satisfaction metrics should improve")]
public async Task ThenCustomerSatisfactionMetricsShouldImprove()
{
    var metricsService = _serviceProvider.GetRequiredService<IMetricsService>();

    // Business KPI validation
    var customerSatisfactionScore = await metricsService.GetCustomerSatisfactionScoreAsync();
    customerSatisfactionScore.Should().BeGreaterThan(4.0,
        "Customer satisfaction should be above 4.0 after UX improvements");

    var supportTicketVolume = await metricsService.GetSupportTicketVolumeAsync(TimeSpan.FromDays(7));
    supportTicketVolume.Should().BeLessThan(_baselineSupportTickets * 0.8,
        "Support ticket volume should decrease by at least 20%");

    var conversionRate = await metricsService.GetConversionRateAsync(TimeSpan.FromDays(30));
    conversionRate.Should().BeGreaterThan(_baselineConversionRate * 1.1,
        "Conversion rate should improve by at least 10%");
}

[Then("the system performance metrics should meet SLA requirements")]
public async Task ThenSystemPerformanceMetricsShouldMeetSLA()
{
    var performanceService = _serviceProvider.GetRequiredService<IPerformanceService>();

    // Performance SLA validation
    var responseTime = await performanceService.GetAverageResponseTimeAsync(TimeSpan.FromHours(1));
    responseTime.Should().BeLessThan(TimeSpan.FromMilliseconds(200),
        "Average response time should be under 200ms per SLA");

    var uptime = await performanceService.GetUptimePercentageAsync(TimeSpan.FromDays(30));
    uptime.Should().BeGreaterThan(99.9,
        "System uptime should be above 99.9% per SLA");

    var errorRate = await performanceService.GetErrorRateAsync(TimeSpan.FromHours(24));
    errorRate.Should().BeLessThan(0.1,
        "Error rate should be below 0.1% per SLA");
}
```

### Regulatory and Compliance Integration

#### GDPR Compliance Testing

```gherkin
Feature: GDPR Compliance for Customer Data
  As a data subject
  I want my personal data rights respected
  So that my privacy is protected per GDPR requirements

Scenario: Customer exercises right to data portability
  Given Sarah is a registered customer with 2 years of purchase history
  And she has provided consent for data processing
  When she requests a complete export of her personal data
  Then she receives a machine-readable file within 30 days
  And the file contains all her personal data in JSON format
  And the file includes her profile, orders, payments, and communication history
  And sensitive data like passwords are excluded from the export
  And she receives confirmation that the export is complete

Scenario: Customer withdraws consent for marketing communications
  Given Marcus has provided consent for marketing emails
  And he has received promotional emails in the past month
  When he withdraws consent for marketing communications
  Then his marketing consent status is immediately updated to "withdrawn"
  And he is automatically removed from all marketing email lists
  And he receives confirmation of consent withdrawal
  And he continues to receive transactional emails only
  And his withdrawal is logged for compliance audit purposes
```

#### SOX Compliance Audit Trail Testing

```csharp
[Then("all financial transactions should have complete audit trails")]
public async Task ThenFinancialTransactionsShouldHaveCompleteAuditTrails()
{
    var auditService = _serviceProvider.GetRequiredService<IAuditService>();
    var orderService = _serviceProvider.GetRequiredService<IOrderService>();

    // Retrieve financial transaction for audit
    var order = await orderService.GetOrderAsync(_currentOrderId);
    var auditTrail = await auditService.GetAuditTrailAsync(
        entityType: "Order",
        entityId: _currentOrderId);

    // SOX compliance validation
    auditTrail.Should().NotBeEmpty("Every financial transaction must have an audit trail");

    auditTrail.Should().ContainSingle(entry =>
        entry.Action == "OrderCreated" &&
        entry.UserId == _currentCustomer.Id &&
        entry.Timestamp >= _testStartTime,
        "Order creation must be logged with user and timestamp");

    auditTrail.Should().ContainSingle(entry =>
        entry.Action == "PaymentProcessed" &&
        entry.Amount == order.TotalAmount &&
        entry.PaymentMethod == order.PaymentMethod,
        "Payment processing must be logged with amount and method");

    auditTrail.Should().ContainSingle(entry =>
        entry.Action == "InventoryUpdated" &&
        entry.ProductId == order.ProductId &&
        entry.QuantityChange == -order.Quantity,
        "Inventory changes must be logged with product and quantity");

    // Immutability validation
    auditTrail.All(entry => entry.IsImmutable).Should().BeTrue(
        "Audit trail entries must be immutable for SOX compliance");
}
```

## Performance Considerations

### Optimizing ATDD Test Execution

#### Test Data Management Strategies

```csharp
public class PerformantTestDataBuilder
{
    private static readonly ConcurrentDictionary<string, object> _dataCache = new();

    public static async Task<Customer> CreatePerformantCustomerAsync()
    {
        // Cache frequently used test data
        var customerTemplate = _dataCache.GetOrAdd("CustomerTemplate",
            _ => new CustomerBuilder().WithStandardDefaults().Build());

        // Clone and customize for specific test
        var customer = customerTemplate.Clone();
        customer.Email = GenerateUniqueEmail();

        // Use production service for realistic data creation
        var customerService = TestServiceProvider.GetRequiredService<ICustomerService>();
        return await customerService.CreateCustomerAsync(customer);
    }

    public static async Task CleanupTestDataAsync(Customer customer)
    {
        // Use production service for realistic cleanup
        var customerService = TestServiceProvider.GetRequiredService<ICustomerService>();
        await customerService.DeleteCustomerAsync(customer.Id);
    }
}
```

#### Parallel Test Execution Patterns

```csharp
[Collection("CustomerRegistration")] // Sequential execution for data integrity
public class CustomerRegistrationTests : IAsyncLifetime
{
    private readonly TestDatabaseFixture _databaseFixture;
    private readonly IServiceProvider _serviceProvider;

    public async Task InitializeAsync()
    {
        // Setup isolated test environment
        await _databaseFixture.ResetDatabaseAsync();
        _serviceProvider = TestServiceFactory.CreateServiceProvider();
    }

    public async Task DisposeAsync()
    {
        // Cleanup test environment
        await _databaseFixture.CleanupAsync();
        _serviceProvider.Dispose();
    }
}

[Collection("ProductCatalog")] // Can run in parallel with CustomerRegistration
public class ProductCatalogTests : IAsyncLifetime
{
    // Parallel execution for independent business domains
}
```

## Troubleshooting Common ATDD Issues

### Issue: Tests Passing with Incomplete Implementation

**Problem**: Acceptance tests pass but business functionality is incomplete
**Root Cause**: Test infrastructure implementing business logic instead of production services
**Solution**:

```csharp
// ❌ Problem: Test passes with incomplete production implementation
[When("customer places order")]
public async Task WhenCustomerPlacesOrder()
{
    // This bypasses production business logic
    _testDatabase.Orders.Add(new Order { CustomerId = _customer.Id, Status = "Complete" });
    await _testDatabase.SaveChangesAsync();
}

// ✅ Solution: Force production service integration
[When("customer places order")]
public async Task WhenCustomerPlacesOrder()
{
    var orderService = _serviceProvider.GetRequiredService<IOrderService>();
    var result = await orderService.CreateOrderAsync(_customer.Id, _orderItems);

    if (!result.IsSuccess)
    {
        throw new InvalidOperationException($"Order creation failed: {result.ErrorMessage}");
    }
}
```

### Issue: Business Stakeholders Can't Understand Tests

**Problem**: Tests written in technical language that business stakeholders can't validate
**Root Cause**: Developer-centric test writing without business perspective
**Solution**:

```gherkin
# ❌ Problem: Technical language
Scenario: PaymentService processes CreditCardTransaction successfully
  Given PaymentGateway.IsAvailable() returns true
  And CreditCard.IsValid() returns true
  When PaymentProcessor.ExecuteTransaction() is invoked
  Then TransactionResult.Status equals "SUCCESS"

# ✅ Solution: Business language
Scenario: Customer completes purchase with credit card
  Given Lisa has a valid credit card on file
  And she has $150 worth of items in her cart
  When she completes the checkout process
  Then her credit card is charged $150
  And she receives an order confirmation email
  And her items are marked for shipping
```

### Issue: Slow Test Execution

**Problem**: ATDD tests running too slowly for effective feedback
**Root Cause**: Inefficient test data setup or unnecessary external dependencies
**Solution**:

```csharp
// ❌ Problem: Slow setup with external calls
[Given("customer has purchase history")]
public async Task GivenCustomerHasPurchaseHistory()
{
    for (int i = 0; i < 10; i++)
    {
        await CreateOrderThroughCompleteWorkflowAsync(); // Slow!
    }
}

// ✅ Solution: Efficient test data creation
[Given("customer has purchase history")]
public async Task GivenCustomerHasPurchaseHistory()
{
    var customerService = _serviceProvider.GetRequiredService<ICustomerService>();
    await customerService.CreateCustomerWithPurchaseHistoryAsync(_customer.Id, orderCount: 10);
}
```

This comprehensive guide provides practical patterns for implementing ATDD effectively while maintaining production service integration and business value focus throughout the development process.
