import type { PropsWithChildren } from 'react';
import React from 'react';
export interface WizardStepContentWrapperProps {
    /**
     * Displayed in header of the step.
     *
     * ex)
     * `<FormattedMessage
     *   defaultMessage="STEP{stepIndex}"
     *   description="Wizard step number"
     *   values={{ stepIndex: stepIndex + 1 }}
     * />`
     */
    header: React.ReactNode;
    /**
     * Title of the step
     */
    title: React.ReactNode;
    /**
     * Description of the step displayed below the step title
     */
    description: React.ReactNode;
    /**
     * Content to display between header and scrollable area, typically used for errors or alerts
     */
    alertContent?: React.ReactNode;
}
export declare function WizardStepContentWrapper({ header, title, description, alertContent, children, }: PropsWithChildren<WizardStepContentWrapperProps>): import("@emotion/react/jsx-runtime").JSX.Element;
//# sourceMappingURL=WizardStepContentWrapper.d.ts.map